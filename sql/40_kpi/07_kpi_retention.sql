-- Repeat purchasing, at the grain of the person rather than the order.
--
-- This is the reason customer_unique_id exists in the model at all. Every other
-- view in this project counts orders; these two count people, and the
-- distinction is not cosmetic: there are 99,441 customer_id values and 96,096
-- customer_unique_id values, so using the wrong one inflates the customer base
-- by the repeat rate.
--
-- RIGHT CENSORING IS THE WHOLE DIFFICULTY.
-- The last purchase in the dataset is 2018-09-03. A customer whose first order
-- fell in August 2018 has had days to come back; one from January 2017 has had
-- eighteen months. Comparing their repeat rates directly would manufacture a
-- decline that is purely an artefact of observation time.
--
-- The fix is a fixed observation window per cohort: every cohort is measured
-- over the SAME number of days after its first purchase, and a cohort is
-- excluded from a window it has not fully lived through. `is_complete` marks
-- this explicitly rather than leaving the reader to infer it.

CREATE OR REPLACE VIEW mart.kpi_customer_orders AS
WITH per_customer AS (
    SELECT
        customer_unique_id,
        count(*)          AS n_orders,
        sum(items_value)  AS lifetime_items_value,
        min(purchased_at) AS first_purchase_at,
        max(purchased_at) AS last_purchase_at
    FROM mart.fct_orders
    WHERE is_sale_eligible
    GROUP BY customer_unique_id
)
SELECT
    n_orders                                        AS orders_per_customer,
    count(*)                                        AS n_customers,
    round(100.0 * count(*) / sum(count(*)) OVER (), 3) AS pct_of_customers,
    sum(n_orders)                                   AS n_orders,
    round(100.0 * sum(n_orders) / sum(sum(n_orders)) OVER (), 2) AS pct_of_orders,
    round(sum(lifetime_items_value), 2)             AS items_value,
    round(100.0 * sum(lifetime_items_value) / sum(sum(lifetime_items_value)) OVER (), 2)
                                                    AS pct_of_items_value,
    round(avg(lifetime_items_value), 2)             AS avg_lifetime_items_value
FROM per_customer
GROUP BY n_orders
ORDER BY n_orders;

-- Cohort retention on a fixed 90-day window.
--
-- Definition: of the customers whose FIRST sale-eligible order fell in month M,
-- what share placed another order within 90 days of that first order?
--
-- A cohort is `is_complete` only when 90 days had elapsed between the end of
-- month M and the last purchase in the dataset. Incomplete cohorts are still
-- listed, with their partial figure, but flagged - dropping them silently would
-- hide the fact that the series is censored at the right edge.
CREATE OR REPLACE VIEW mart.kpi_cohort_retention_90d AS
WITH bounds AS (
    SELECT max(purchased_at) AS dataset_last_purchase_at
    FROM mart.fct_orders WHERE is_sale_eligible
),
first_order AS (
    SELECT
        customer_unique_id,
        min(purchased_at) AS first_purchase_at
    FROM mart.fct_orders
    WHERE is_sale_eligible
    GROUP BY customer_unique_id
),
repeats AS (
    SELECT
        f.customer_unique_id,
        f.first_purchase_at,
        CAST(date_trunc('month', f.first_purchase_at) AS DATE) AS cohort_month,
        count(o.order_id) FILTER (
            WHERE o.purchased_at > f.first_purchase_at
              AND o.purchased_at <= f.first_purchase_at + INTERVAL 90 DAY
        ) AS repeat_orders_90d
    FROM first_order f
    LEFT JOIN mart.fct_orders o
           ON o.customer_unique_id = f.customer_unique_id
          AND o.is_sale_eligible
    GROUP BY f.customer_unique_id, f.first_purchase_at
)
SELECT
    r.cohort_month,
    count(*)                                       AS n_new_customers,
    count(*) FILTER (WHERE r.repeat_orders_90d > 0) AS n_repeated_within_90d,
    round(100.0 * count(*) FILTER (WHERE r.repeat_orders_90d > 0) / count(*), 2)
                                                   AS repeat_rate_90d_pct,
    round(wilson_lower(count(*) FILTER (WHERE r.repeat_orders_90d > 0), count(*), 1.959964), 2)
                                                   AS ci_lower_pct,
    round(wilson_upper(count(*) FILTER (WHERE r.repeat_orders_90d > 0), count(*), 1.959964), 2)
                                                   AS ci_upper_pct,
    -- The cohort has lived a full 90 days only if the month ended at least
    -- 90 days before the dataset does.
    (r.cohort_month + INTERVAL 1 MONTH + INTERVAL 90 DAY
        <= any_value(b.dataset_last_purchase_at))  AS is_complete
FROM repeats r
CROSS JOIN bounds b
GROUP BY r.cohort_month
ORDER BY r.cohort_month;
