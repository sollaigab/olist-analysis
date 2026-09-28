-- Collapse the item fan-out to exactly one row per order.
-- This is the whole defence against multiplied amounts: nothing downstream
-- ever joins stg.order_items directly to an order-grain table.
-- 112,650 item rows -> 98,666 order rows.
CREATE OR REPLACE TABLE int.items_by_order AS
SELECT
    order_id,
    count(*)                        AS n_items,
    count(DISTINCT product_id)      AS n_distinct_products,
    count(DISTINCT seller_id)       AS n_sellers,
    sum(item_price)                 AS items_value,      -- merchandise value only
    sum(freight_value)              AS freight_value,    -- shipping, kept separate
    sum(item_price) + sum(freight_value) AS items_plus_freight,  -- NOT profit, NOT revenue
    min(item_price)                 AS min_item_price,
    max(item_price)                 AS max_item_price,
    max(shipping_limit_at)          AS last_shipping_limit_at
FROM stg.order_items
GROUP BY order_id;
