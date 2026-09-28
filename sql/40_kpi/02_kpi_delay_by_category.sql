-- Q2a: which categories concentrate delays?
--
-- Counting rule: an order is counted ONCE PER CATEGORY it contains, via
-- count(DISTINCT order_id). A 3-item order in one category contributes 1, not
-- 3. A 2-category order contributes 1 to each of its categories. Category
-- shares of orders therefore sum to more than 100%, which is correct and is
-- stated here rather than hidden by forcing a single category onto every order.
CREATE OR REPLACE VIEW mart.kpi_delay_by_category AS
SELECT
    category,
    count(DISTINCT order_id)                        AS n_orders,
    count(DISTINCT order_id) FILTER (WHERE is_late) AS n_late_orders,
    round(100.0 * count(DISTINCT order_id) FILTER (WHERE is_late)
                / nullif(count(DISTINCT order_id), 0), 2) AS late_rate_pct,
    median(delay_days)                              AS median_delay_days,
    quantile_cont(delay_days, 0.9)                  AS p90_delay_days,
    median(delivery_days)                           AS median_delivery_days,
    sum(item_price)                                 AS items_value,
    sum(item_price) FILTER (WHERE is_late)          AS items_value_late_orders,
    round(avg(item_price), 2)                       AS avg_item_price,
    round(100.0 * count(*) FILTER (WHERE is_interstate) / count(*), 1) AS interstate_pct
FROM mart.fct_order_items
WHERE has_delivery_measurement AND in_analysis_window
GROUP BY category
HAVING count(DISTINCT order_id) >= 100
ORDER BY n_late_orders DESC;
