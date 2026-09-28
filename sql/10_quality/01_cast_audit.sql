-- Did any explicit cast silently destroy data?
-- A raw value that is present and non-blank but NULL after TRY_CAST is a
-- malformed value. This table makes that count visible instead of leaving it
-- to be discovered downstream as a mysteriously missing row.
CREATE OR REPLACE TABLE qa.cast_audit AS
WITH checks AS (
    SELECT 'orders.order_purchase_timestamp' AS column_checked,
           count(*) FILTER (WHERE order_purchase_timestamp IS NOT NULL
                              AND trim(order_purchase_timestamp) <> ''
                              AND TRY_CAST(order_purchase_timestamp AS TIMESTAMP) IS NULL) AS failed_casts,
           count(*) FILTER (WHERE order_purchase_timestamp IS NULL
                              OR trim(order_purchase_timestamp) = '')                      AS blank_source
    FROM raw.orders
    UNION ALL
    SELECT 'orders.order_delivered_customer_date',
           count(*) FILTER (WHERE order_delivered_customer_date IS NOT NULL
                              AND trim(order_delivered_customer_date) <> ''
                              AND TRY_CAST(order_delivered_customer_date AS TIMESTAMP) IS NULL),
           count(*) FILTER (WHERE order_delivered_customer_date IS NULL
                              OR trim(order_delivered_customer_date) = '')
    FROM raw.orders
    UNION ALL
    SELECT 'orders.order_estimated_delivery_date',
           count(*) FILTER (WHERE order_estimated_delivery_date IS NOT NULL
                              AND trim(order_estimated_delivery_date) <> ''
                              AND TRY_CAST(order_estimated_delivery_date AS TIMESTAMP) IS NULL),
           count(*) FILTER (WHERE order_estimated_delivery_date IS NULL
                              OR trim(order_estimated_delivery_date) = '')
    FROM raw.orders
    UNION ALL
    SELECT 'orders.order_approved_at',
           count(*) FILTER (WHERE order_approved_at IS NOT NULL
                              AND trim(order_approved_at) <> ''
                              AND TRY_CAST(order_approved_at AS TIMESTAMP) IS NULL),
           count(*) FILTER (WHERE order_approved_at IS NULL OR trim(order_approved_at) = '')
    FROM raw.orders
    UNION ALL
    SELECT 'orders.order_delivered_carrier_date',
           count(*) FILTER (WHERE order_delivered_carrier_date IS NOT NULL
                              AND trim(order_delivered_carrier_date) <> ''
                              AND TRY_CAST(order_delivered_carrier_date AS TIMESTAMP) IS NULL),
           count(*) FILTER (WHERE order_delivered_carrier_date IS NULL
                              OR trim(order_delivered_carrier_date) = '')
    FROM raw.orders
    UNION ALL
    SELECT 'order_items.price',
           count(*) FILTER (WHERE price IS NOT NULL AND trim(price) <> ''
                              AND TRY_CAST(price AS DECIMAL(12,2)) IS NULL),
           count(*) FILTER (WHERE price IS NULL OR trim(price) = '')
    FROM raw.order_items
    UNION ALL
    SELECT 'order_items.freight_value',
           count(*) FILTER (WHERE freight_value IS NOT NULL AND trim(freight_value) <> ''
                              AND TRY_CAST(freight_value AS DECIMAL(12,2)) IS NULL),
           count(*) FILTER (WHERE freight_value IS NULL OR trim(freight_value) = '')
    FROM raw.order_items
    UNION ALL
    SELECT 'order_payments.payment_value',
           count(*) FILTER (WHERE payment_value IS NOT NULL AND trim(payment_value) <> ''
                              AND TRY_CAST(payment_value AS DECIMAL(12,2)) IS NULL),
           count(*) FILTER (WHERE payment_value IS NULL OR trim(payment_value) = '')
    FROM raw.order_payments
    UNION ALL
    SELECT 'order_reviews.review_score',
           count(*) FILTER (WHERE review_score IS NOT NULL AND trim(review_score) <> ''
                              AND TRY_CAST(review_score AS SMALLINT) IS NULL),
           count(*) FILTER (WHERE review_score IS NULL OR trim(review_score) = '')
    FROM raw.order_reviews
    UNION ALL
    SELECT 'geolocation.geolocation_lat',
           count(*) FILTER (WHERE geolocation_lat IS NOT NULL AND trim(geolocation_lat) <> ''
                              AND TRY_CAST(geolocation_lat AS DOUBLE) IS NULL),
           count(*) FILTER (WHERE geolocation_lat IS NULL OR trim(geolocation_lat) = '')
    FROM raw.geolocation
)
SELECT * FROM checks ORDER BY failed_casts DESC, column_checked;
