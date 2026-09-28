-- Grain: 1 row = 1 order. Key: order_id.
-- TRY_CAST so a malformed timestamp becomes NULL instead of killing the build.
-- sql/10_quality/01_cast_audit.sql counts how many did, so nothing goes missing
-- quietly.
CREATE OR REPLACE TABLE stg.orders AS
SELECT
    order_id,
    customer_id,                              -- per-order customer key, NOT the person
    order_status,
    TRY_CAST(order_purchase_timestamp     AS TIMESTAMP) AS purchased_at,
    TRY_CAST(order_approved_at            AS TIMESTAMP) AS approved_at,
    TRY_CAST(order_delivered_carrier_date AS TIMESTAMP) AS delivered_carrier_at,
    TRY_CAST(order_delivered_customer_date AS TIMESTAMP) AS delivered_customer_at,
    TRY_CAST(order_estimated_delivery_date AS TIMESTAMP) AS estimated_delivery_at
FROM raw.orders;
