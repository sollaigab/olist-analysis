-- Rules that encode what the data is *supposed* to mean, as opposed to what it
-- is merely shaped like. Each row carries a status so the suite can be read at
-- a glance and asserted on in tests/.
--   FAIL : contradicts the model; downstream code must exclude or handle it
--   INFO : real characteristic of the data, documented, not an error
CREATE OR REPLACE TABLE qa.business_checks AS
SELECT * FROM (
    SELECT 'delivered orders missing a delivery date' AS rule,
           count(*)                                   AS n_rows,
           'FAIL'                                     AS status,
           'status says delivered but the timestamp is absent; excluded from all delay KPIs' AS handling
    FROM stg.orders
    WHERE order_status = 'delivered' AND delivered_customer_at IS NULL
    UNION ALL
    SELECT 'delivery to customer earlier than handover to carrier', count(*), 'FAIL',
           'physically impossible ordering; flagged, excluded from lead-time medians'
    FROM stg.orders
    WHERE delivered_customer_at IS NOT NULL AND delivered_carrier_at IS NOT NULL
      AND delivered_customer_at < delivered_carrier_at
    UNION ALL
    SELECT 'delivery earlier than purchase', count(*), 'FAIL', 'must be 0'
    FROM stg.orders
    WHERE delivered_customer_at IS NOT NULL AND delivered_customer_at < purchased_at
    UNION ALL
    SELECT 'approval earlier than purchase', count(*), 'FAIL', 'must be 0'
    FROM stg.orders
    WHERE approved_at IS NOT NULL AND approved_at < purchased_at
    UNION ALL
    SELECT 'item price <= 0', count(*), 'FAIL', 'must be 0 for a marketplace sale'
    FROM stg.order_items WHERE item_price <= 0
    UNION ALL
    SELECT 'freight value < 0', count(*), 'FAIL', 'must be 0'
    FROM stg.order_items WHERE freight_value < 0
    UNION ALL
    SELECT 'payment value <= 0', count(*), 'INFO',
           'zero-value payment lines (vouchers covering the full amount); kept, never used as revenue'
    FROM stg.order_payments WHERE payment_value <= 0
    UNION ALL
    SELECT 'review_id reused across different orders', count(*), 'INFO',
           'review_id is NOT a primary key; the grain is (review_id, order_id)'
    FROM (SELECT review_id FROM stg.order_reviews GROUP BY 1 HAVING count(DISTINCT order_id) > 1)
    UNION ALL
    SELECT 'orders carrying more than one review', count(*), 'INFO',
           'collapsed to one review per order in 20_intermediate; rule documented there'
    FROM (SELECT order_id FROM stg.order_reviews GROUP BY 1 HAVING count(*) > 1)
    UNION ALL
    SELECT 'orders fulfilled by more than one seller', count(*), 'INFO',
           'excluded from any seller-level review attribution'
    FROM (SELECT order_id FROM stg.order_items GROUP BY 1 HAVING count(DISTINCT seller_id) > 1)
    UNION ALL
    SELECT 'repeat customers (customer_unique_id with >1 order)', count(*), 'INFO',
           'why customer counts must use customer_unique_id, not customer_id'
    FROM (SELECT customer_unique_id FROM stg.customers GROUP BY 1 HAVING count(*) > 1)
    UNION ALL
    SELECT 'orders in sparse boundary months (before 2017-01 or after 2018-08)', count(*), 'INFO',
           'partial months at both ends; time series is trimmed to 2017-01..2018-08'
    FROM stg.orders
    WHERE purchased_at < TIMESTAMP '2017-01-01' OR purchased_at >= TIMESTAMP '2018-09-01'
) ORDER BY status, n_rows DESC;
