-- Grain: 1 row = 1 product. Key: product_id.
-- The source spells two columns 'lenght'. Renamed here deliberately; the
-- rename is documented in reports/data_dictionary.md so the lineage back to
-- the raw column is never ambiguous.
CREATE OR REPLACE TABLE stg.products AS
SELECT
    product_id,
    product_category_name                                  AS category_pt,
    TRY_CAST(product_name_lenght        AS INTEGER)        AS name_length,        -- raw: product_name_lenght
    TRY_CAST(product_description_lenght AS INTEGER)        AS description_length, -- raw: product_description_lenght
    TRY_CAST(product_photos_qty AS INTEGER)                AS photos_qty,
    TRY_CAST(product_weight_g   AS INTEGER)                AS weight_g,
    TRY_CAST(product_length_cm  AS INTEGER)                AS length_cm,
    TRY_CAST(product_height_cm  AS INTEGER)                AS height_cm,
    TRY_CAST(product_width_cm   AS INTEGER)                AS width_cm
FROM raw.products;
