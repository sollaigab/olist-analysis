-- Grain: 1 row = 1 item line within an order. Key: (order_id, order_item_id).
-- This is the fan-out table: 112,650 rows against 99,441 orders.
-- Monetary columns are DECIMAL, never FLOAT: binary floats do not represent
-- 0.01 exactly, and summing 112k of them drifts.
CREATE OR REPLACE TABLE stg.order_items AS
SELECT
    order_id,
    TRY_CAST(order_item_id AS INTEGER)        AS order_item_id,
    product_id,
    seller_id,
    TRY_CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_at,
    TRY_CAST(price         AS DECIMAL(12,2))   AS item_price,
    TRY_CAST(freight_value AS DECIMAL(12,2))   AS freight_value
FROM raw.order_items;
