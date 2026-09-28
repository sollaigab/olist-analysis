-- Grain: 1 row = 1 Portuguese category name. Key: category_pt.
-- Only 71 rows against the distinct categories present in products: the
-- coverage gap is measured in 10_quality rather than assumed to be zero.
CREATE OR REPLACE TABLE stg.category_translation AS
SELECT
    product_category_name         AS category_pt,
    product_category_name_english AS category_en
FROM raw.category_translation;
