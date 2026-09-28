-- Grain: 1 row = 1 seller. Key: seller_id.
CREATE OR REPLACE TABLE stg.sellers AS
SELECT
    seller_id,
    lpad(seller_zip_code_prefix, 5, '0') AS seller_zip_prefix,
    lower(trim(seller_city))             AS seller_city,
    upper(trim(seller_state))            AS seller_state
FROM raw.sellers;
