-- Which rows on one side of a relationship have no counterpart on the other?
-- Orphans are not automatically errors here: an 'unavailable' order legitimately
-- has no items. The point is that every orphan is counted and explained, so no
-- downstream join loses rows by surprise.
CREATE OR REPLACE TABLE qa.referential_checks AS
SELECT 'orders without any item'    AS relationship,
       count(*)                     AS n_orphans,
       'expected for unavailable/canceled orders' AS note
FROM stg.orders o
WHERE NOT EXISTS (SELECT 1 FROM stg.order_items i WHERE i.order_id = o.order_id)
UNION ALL
SELECT 'orders without any payment', count(*), 'investigate individually if small'
FROM stg.orders o
WHERE NOT EXISTS (SELECT 1 FROM stg.order_payments p WHERE p.order_id = o.order_id)
UNION ALL
SELECT 'orders without any review', count(*), 'drives the review-coverage denominator'
FROM stg.orders o
WHERE NOT EXISTS (SELECT 1 FROM stg.order_reviews r WHERE r.order_id = o.order_id)
UNION ALL
SELECT 'items pointing at a missing order', count(*), 'must be 0'
FROM stg.order_items i
WHERE NOT EXISTS (SELECT 1 FROM stg.orders o WHERE o.order_id = i.order_id)
UNION ALL
SELECT 'items pointing at a missing product', count(*), 'must be 0'
FROM stg.order_items i
WHERE NOT EXISTS (SELECT 1 FROM stg.products p WHERE p.product_id = i.product_id)
UNION ALL
SELECT 'items pointing at a missing seller', count(*), 'must be 0'
FROM stg.order_items i
WHERE NOT EXISTS (SELECT 1 FROM stg.sellers s WHERE s.seller_id = i.seller_id)
UNION ALL
SELECT 'orders pointing at a missing customer', count(*), 'must be 0'
FROM stg.orders o
WHERE NOT EXISTS (SELECT 1 FROM stg.customers c WHERE c.customer_id = o.customer_id)
UNION ALL
SELECT 'reviews pointing at a missing order', count(*), 'must be 0'
FROM stg.order_reviews r
WHERE NOT EXISTS (SELECT 1 FROM stg.orders o WHERE o.order_id = r.order_id)
UNION ALL
SELECT 'products with an untranslatable category', count(DISTINCT p.category_pt),
       'category stays in Portuguese for these'
FROM stg.products p
LEFT JOIN stg.category_translation t ON t.category_pt = p.category_pt
WHERE p.category_pt IS NOT NULL AND t.category_en IS NULL
UNION ALL
SELECT 'products with no category at all', count(*), 'bucketed as unknown downstream'
FROM stg.products WHERE category_pt IS NULL
UNION ALL
SELECT 'customer zip prefixes absent from geolocation', count(DISTINCT c.customer_zip_prefix),
       'limits map coverage, not order counts'
FROM stg.customers c
LEFT JOIN stg.geolocation g ON g.zip_prefix = c.customer_zip_prefix
WHERE g.zip_prefix IS NULL;
