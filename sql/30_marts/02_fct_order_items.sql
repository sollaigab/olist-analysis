-- ONE ROW PER ITEM LINE. 112,650 rows, always.
--
-- Exists because category and seller are properties of an item, not of an
-- order: an order containing a watch and a mattress has no single category.
--
-- USAGE CONTRACT:
--   sums of item_price / freight_value here are correct;
--   counts of orders here MUST use count(DISTINCT order_id), never count(*);
--   order-level flags are repeated on every line of the order, so averaging
--   delay_days over this table weights an order by its number of items.
--   Order-level rates belong in mart.fct_orders.
CREATE OR REPLACE TABLE mart.fct_order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,

    i.item_price,
    i.freight_value,

    -- Product attributes, denormalised
    coalesce(t.category_en, p.category_pt, 'unknown') AS category,
    (p.category_pt IS NULL)                           AS category_missing,
    (p.category_pt IS NOT NULL AND t.category_en IS NULL) AS category_untranslated,
    p.weight_g,
    p.photos_qty,

    -- Seller attributes
    s.seller_state,
    s.seller_city,

    -- Order context, repeated per line (see usage contract above)
    o.purchase_month,
    o.customer_state,
    o.order_status,
    o.is_sale_eligible,
    o.has_delivery_measurement,
    o.is_late,
    o.delay_days,
    o.delivery_days,
    o.review_score,
    o.has_review,
    o.is_multi_seller,
    o.in_analysis_window,

    -- Cross-state shipments travel further; useful when reading regional delay
    (s.seller_state IS NOT NULL AND o.customer_state IS NOT NULL
     AND s.seller_state <> o.customer_state)          AS is_interstate

FROM stg.order_items i
JOIN mart.fct_orders o ON o.order_id = i.order_id
LEFT JOIN stg.products p ON p.product_id = i.product_id
LEFT JOIN stg.category_translation t ON t.category_pt = p.category_pt
LEFT JOIN stg.sellers s ON s.seller_id = i.seller_id;
