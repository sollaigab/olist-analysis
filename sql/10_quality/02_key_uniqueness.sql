-- Is every declared key actually unique, and is every declared 1:N really 1:N?
-- Declaring a grain is worthless unless it is tested; these are the assertions
-- the rest of the model rests on.
CREATE OR REPLACE TABLE qa.key_checks AS
SELECT 'stg.orders / order_id'                AS declared_key,
       count(*) AS rows, count(DISTINCT order_id) AS distinct_keys,
       count(*) - count(DISTINCT order_id)    AS duplicate_rows,
       'unique'  AS expectation
FROM stg.orders
UNION ALL
SELECT 'stg.customers / customer_id',
       count(*), count(DISTINCT customer_id), count(*) - count(DISTINCT customer_id), 'unique'
FROM stg.customers
UNION ALL
SELECT 'stg.customers / customer_unique_id',
       count(*), count(DISTINCT customer_unique_id),
       count(*) - count(DISTINCT customer_unique_id), 'NOT unique (repeat buyers)'
FROM stg.customers
UNION ALL
SELECT 'stg.order_items / (order_id, order_item_id)',
       count(*), count(DISTINCT (order_id, order_item_id)),
       count(*) - count(DISTINCT (order_id, order_item_id)), 'unique'
FROM stg.order_items
UNION ALL
SELECT 'stg.order_items / order_id',
       count(*), count(DISTINCT order_id), count(*) - count(DISTINCT order_id),
       'NOT unique (fan-out)'
FROM stg.order_items
UNION ALL
SELECT 'stg.order_payments / (order_id, payment_sequential)',
       count(*), count(DISTINCT (order_id, payment_sequential)),
       count(*) - count(DISTINCT (order_id, payment_sequential)), 'unique'
FROM stg.order_payments
UNION ALL
SELECT 'stg.order_payments / order_id',
       count(*), count(DISTINCT order_id), count(*) - count(DISTINCT order_id),
       'NOT unique (split payments)'
FROM stg.order_payments
UNION ALL
SELECT 'stg.order_reviews / review_id',
       count(*), count(DISTINCT review_id), count(*) - count(DISTINCT review_id), 'unique'
FROM stg.order_reviews
UNION ALL
SELECT 'stg.order_reviews / order_id',
       count(*), count(DISTINCT order_id), count(*) - count(DISTINCT order_id),
       'NOT unique (multiple reviews)'
FROM stg.order_reviews
UNION ALL
SELECT 'stg.products / product_id',
       count(*), count(DISTINCT product_id), count(*) - count(DISTINCT product_id), 'unique'
FROM stg.products
UNION ALL
SELECT 'stg.sellers / seller_id',
       count(*), count(DISTINCT seller_id), count(*) - count(DISTINCT seller_id), 'unique'
FROM stg.sellers
UNION ALL
SELECT 'stg.geolocation / zip_prefix',
       count(*), count(DISTINCT zip_prefix), count(*) - count(DISTINCT zip_prefix), 'unique'
FROM stg.geolocation
ORDER BY declared_key;
