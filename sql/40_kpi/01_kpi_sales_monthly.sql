-- Q1: how does the value of sold items move over time?
-- Order grain, so amounts cannot be multiplied. Boundary months excluded via
-- in_analysis_window: they hold 4, 1, 16 and 4 orders respectively.
CREATE OR REPLACE VIEW mart.kpi_sales_monthly AS
SELECT
    purchase_month,
    count(*)                                    AS n_orders,
    count(DISTINCT customer_unique_id)          AS n_customers,
    count(*) FILTER (WHERE items_value IS NULL) AS n_orders_without_items,
    sum(items_value)                            AS items_value,
    sum(freight_value)                          AS freight_value,
    sum(items_plus_freight)                     AS items_plus_freight,
    sum(payments_value)                         AS payments_value,
    sum(n_items)                                AS n_item_lines,
    round(sum(items_value) / nullif(count(*) FILTER (WHERE items_value IS NOT NULL), 0), 2) AS aov,
    round(sum(items_value) / nullif(sum(n_items), 0), 2)               AS avg_item_price,
    round(100.0 * sum(freight_value) / nullif(sum(items_value), 0), 2) AS freight_pct_of_items
FROM mart.fct_orders
WHERE is_sale_eligible AND in_analysis_window
GROUP BY purchase_month
ORDER BY purchase_month;
