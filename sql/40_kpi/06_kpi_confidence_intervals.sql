-- Uncertainty on every rate.
--
-- The project has shown group sizes from the start, but showing n is not the
-- same as using it. AL's 21.46% rests on 396 orders and SP's 4.50% on 40,399;
-- printing both to two decimals implies a precision the smaller group does not
-- have. These views attach an interval to each rate so the comparison is
-- honest.
--
-- WILSON SCORE INTERVAL, not the normal approximation.
-- The textbook p +/- z*sqrt(p(1-p)/n) misbehaves exactly where this data lives:
-- small groups with proportions near zero. It can produce a negative lower
-- bound, and its coverage degrades badly below roughly n*p = 5. The Wilson
-- interval stays inside [0,1] by construction and holds its nominal coverage
-- at small n, which is why it is the standard choice for exactly this case.
--
--   centre = (p + z^2/2n) / (1 + z^2/n)
--   half   = z/(1 + z^2/n) * sqrt( p(1-p)/n + z^2/(4n^2) )
--
-- z = 1.959964 for a 95% interval.
--
-- WHAT THE INTERVAL DOES AND DOES NOT MEAN.
-- It describes sampling variability only: how much this rate would move if the
-- same process generated another set of orders of the same size. It says
-- nothing about whether the dataset is representative, whether the anonymised
-- sample is biased, or whether 2018 resembles today. Those are larger problems
-- than an interval can express.

-- greatest/least clamp to [0,100]: the Wilson bounds are inside the interval
-- analytically, but floating-point arithmetic can return -1e-17, which
-- serialises into a CSV as "-0.00" and reads as a negative probability.
CREATE OR REPLACE MACRO wilson_lower(successes, trials, z) AS (
    CASE WHEN trials IS NULL OR trials = 0 THEN NULL ELSE
        greatest(0.0, 100.0 * (
            ((successes::DOUBLE / trials) + z * z / (2 * trials))
            / (1 + z * z / trials)
            - (z / (1 + z * z / trials))
              * sqrt(
                  (successes::DOUBLE / trials) * (1 - successes::DOUBLE / trials) / trials
                  + z * z / (4.0 * trials * trials)
                )
        ))
    END
);

CREATE OR REPLACE MACRO wilson_upper(successes, trials, z) AS (
    CASE WHEN trials IS NULL OR trials = 0 THEN NULL ELSE
        least(100.0, 100.0 * (
            ((successes::DOUBLE / trials) + z * z / (2 * trials))
            / (1 + z * z / trials)
            + (z / (1 + z * z / trials))
              * sqrt(
                  (successes::DOUBLE / trials) * (1 - successes::DOUBLE / trials) / trials
                  + z * z / (4.0 * trials * trials)
                )
        ))
    END
);

-- State late rates with 95% intervals, and an explicit verdict against the
-- national rate. `verdict` compares the interval to the benchmark rather than
-- comparing point estimates, which is the whole reason the view exists.
CREATE OR REPLACE VIEW mart.kpi_state_late_rate_ci AS
WITH benchmark AS (
    SELECT 100.0 * count(*) FILTER (WHERE is_late) / count(*) AS national_rate_pct
    FROM mart.fct_orders
    WHERE has_delivery_measurement AND in_analysis_window
),
rates AS (
    SELECT
        customer_state,
        count(*)                        AS n_orders,
        count(*) FILTER (WHERE is_late) AS n_late_orders,
        round(100.0 * count(*) FILTER (WHERE is_late) / count(*), 2) AS late_rate_pct,
        round(wilson_lower(count(*) FILTER (WHERE is_late), count(*), 1.959964), 2) AS ci_lower_pct,
        round(wilson_upper(count(*) FILTER (WHERE is_late), count(*), 1.959964), 2) AS ci_upper_pct
    FROM mart.fct_orders
    WHERE has_delivery_measurement AND in_analysis_window
    GROUP BY customer_state
)
SELECT
    r.customer_state,
    r.n_orders,
    r.n_late_orders,
    r.late_rate_pct,
    r.ci_lower_pct,
    r.ci_upper_pct,
    round(r.ci_upper_pct - r.ci_lower_pct, 2) AS ci_width_pp,
    round(b.national_rate_pct, 2)             AS national_rate_pct,
    CASE
        WHEN r.ci_lower_pct > b.national_rate_pct THEN 'worse than national'
        WHEN r.ci_upper_pct < b.national_rate_pct THEN 'better than national'
        ELSE 'not distinguishable'
    END AS verdict
FROM rates r
CROSS JOIN benchmark b
ORDER BY r.late_rate_pct DESC, r.customer_state;

-- Same treatment for categories. This is where the intervals earn their keep:
-- `audio` has the highest point estimate of any category and an interval wide
-- enough to swallow the national rate.
CREATE OR REPLACE VIEW mart.kpi_category_late_rate_ci AS
WITH benchmark AS (
    SELECT 100.0 * count(*) FILTER (WHERE is_late) / count(*) AS national_rate_pct
    FROM mart.fct_orders
    WHERE has_delivery_measurement AND in_analysis_window
),
rates AS (
    SELECT
        category,
        count(DISTINCT order_id)                        AS n_orders,
        count(DISTINCT order_id) FILTER (WHERE is_late) AS n_late_orders
    FROM mart.fct_order_items
    WHERE has_delivery_measurement AND in_analysis_window
    GROUP BY category
    HAVING count(DISTINCT order_id) >= 100
)
SELECT
    r.category,
    r.n_orders,
    r.n_late_orders,
    round(100.0 * r.n_late_orders / r.n_orders, 2)                       AS late_rate_pct,
    round(wilson_lower(r.n_late_orders, r.n_orders, 1.959964), 2)        AS ci_lower_pct,
    round(wilson_upper(r.n_late_orders, r.n_orders, 1.959964), 2)        AS ci_upper_pct,
    round(wilson_upper(r.n_late_orders, r.n_orders, 1.959964)
        - wilson_lower(r.n_late_orders, r.n_orders, 1.959964), 2)        AS ci_width_pp,
    round(b.national_rate_pct, 2)                                        AS national_rate_pct,
    CASE
        WHEN wilson_lower(r.n_late_orders, r.n_orders, 1.959964) > b.national_rate_pct
            THEN 'worse than national'
        WHEN wilson_upper(r.n_late_orders, r.n_orders, 1.959964) < b.national_rate_pct
            THEN 'better than national'
        ELSE 'not distinguishable'
    END AS verdict
FROM rates r
CROSS JOIN benchmark b
ORDER BY late_rate_pct DESC, r.category;
