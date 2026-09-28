-- Q4: which problems deserve attention once BOTH rate and volume are weighed?
--
-- A category with a 40% late rate on 120 orders and one with a 9% late rate on
-- 9,000 orders are different problems; ranking on either column alone picks the
-- wrong one. This view carries both, plus the absolute count of late orders,
-- which is the quantity an operations team actually has to work through.
--
-- excess_late_orders = how many late orders would disappear if this category
-- performed at the overall late rate. It is an arithmetic gap, NOT a forecast
-- of what a fix would save, and not a claim that the category causes lateness.
CREATE OR REPLACE VIEW mart.kpi_category_priority AS
WITH overall AS (
    SELECT 100.0 * count(*) FILTER (WHERE is_late) / count(*) AS overall_late_rate_pct
    FROM mart.fct_orders
    WHERE has_delivery_measurement AND in_analysis_window
)
SELECT
    c.category,
    c.n_orders,
    c.n_late_orders,
    c.late_rate_pct,
    round(o.overall_late_rate_pct, 2)                AS benchmark_late_rate_pct,
    round(c.late_rate_pct - o.overall_late_rate_pct, 2) AS rate_gap_pp,
    round(c.n_late_orders - c.n_orders * o.overall_late_rate_pct / 100.0, 0) AS excess_late_orders,
    c.median_delay_days,
    c.p90_delay_days,
    c.items_value,
    c.items_value_late_orders,
    round(100.0 * c.items_value_late_orders / nullif(c.items_value, 0), 2) AS pct_items_value_in_late_orders,
    c.interstate_pct
FROM mart.kpi_delay_by_category c
CROSS JOIN overall o
ORDER BY excess_late_orders DESC;

-- Same idea at state level.
CREATE OR REPLACE VIEW mart.kpi_state_priority AS
WITH overall AS (
    SELECT 100.0 * count(*) FILTER (WHERE is_late) / count(*) AS overall_late_rate_pct
    FROM mart.fct_orders
    WHERE has_delivery_measurement AND in_analysis_window
)
SELECT
    s.customer_state,
    s.n_orders,
    s.n_late_orders,
    s.late_rate_pct,
    round(s.late_rate_pct - o.overall_late_rate_pct, 2) AS rate_gap_pp,
    round(s.n_late_orders - s.n_orders * o.overall_late_rate_pct / 100.0, 0) AS excess_late_orders,
    s.median_delivery_days,
    s.median_promised_days,
    s.median_handover_days,
    s.mean_review_score,
    s.n_reviewed_orders,
    s.items_value
FROM mart.kpi_delay_by_state s
CROSS JOIN overall o
ORDER BY excess_late_orders DESC;
