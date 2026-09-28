-- Grain: 1 row = 1 customer_id = 1 order's customer record.
-- customer_id  : surrogate key regenerated per order -> join key.
-- customer_unique_id : the actual person -> use for customer counts, retention.
-- Confusing the two inflates the customer base by the repeat-purchase rate.
-- zip prefix stays VARCHAR: '01037' is a real Sao Paulo prefix and casting to
-- INTEGER would silently turn it into 1037.
CREATE OR REPLACE TABLE stg.customers AS
SELECT
    customer_id,
    customer_unique_id,
    lpad(customer_zip_code_prefix, 5, '0') AS customer_zip_prefix,
    lower(trim(customer_city))             AS customer_city,
    upper(trim(customer_state))            AS customer_state
FROM raw.customers;
