-- Q2b: which areas concentrate delays?
-- Order grain: each order counts once for its customer state, regardless of
-- how many items it held.
CREATE OR REPLACE VIEW mart.kpi_delay_by_state AS
SELECT
    customer_state,
    count(*)                                        AS n_orders,
    count(*) FILTER (WHERE is_late)                 AS n_late_orders,
    round(100.0 * count(*) FILTER (WHERE is_late) / count(*), 2) AS late_rate_pct,
    median(delay_days)                              AS median_delay_days,
    quantile_cont(delay_days, 0.9)                  AS p90_delay_days,
    median(delivery_days)                           AS median_delivery_days,
    median(promised_days)                           AS median_promised_days,
    median(handover_days)                           AS median_handover_days,
    sum(items_value)                                AS items_value,
    round(avg(review_score), 3)                     AS mean_review_score,
    count(*) FILTER (WHERE has_review)              AS n_reviewed_orders
FROM mart.fct_orders
WHERE has_delivery_measurement AND in_analysis_window
GROUP BY customer_state
ORDER BY n_late_orders DESC;
