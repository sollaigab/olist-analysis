-- Grain: 1 row = 1 order. Key: order_id.
-- Casts are explicit and TRY_CAST-based: a malformed timestamp becomes NULL
-- rather than aborting the build, and sql/10_quality/ counts how many did so,
-- so the failure is measured instead of hidden.
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
