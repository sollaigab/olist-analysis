-- ONE ROW PER ORDER. 99,441 rows, always.
--
-- Every contributing table was already collapsed to order grain in
-- 20_intermediate, so these joins cannot multiply a single amount.
--
-- The mart carries flags, not filters. Nothing is thrown away here; the KPI
-- layer decides what to exclude and says so out loud. That way a stakeholder
-- asking "does this include cancellations?" gets an answer from one visible
-- WHERE clause instead of from archaeology.
--
-- Delay is measured at DATE granularity, not timestamp granularity.
-- order_estimated_delivery_date carries no time component (it is always
-- midnight), so comparing it to a delivery timestamp of 09:00 would mark a
-- same-day delivery as late by 9 hours. Business convention: a delivery on the
-- promised calendar day is on time.
CREATE OR REPLACE TABLE mart.fct_orders AS
SELECT
    o.order_id,

    -- Customer keys: two different things, both carried deliberately.
    o.customer_id,                                  -- per-order key, for joins
    c.customer_unique_id,                           -- the person, for customer counts
    c.customer_state,
    c.customer_city,
    c.customer_zip_prefix,
    g.lat  AS customer_lat,
    g.lng  AS customer_lng,

    o.order_status,

    -- Time
    o.purchased_at,
    CAST(date_trunc('month', o.purchased_at) AS DATE) AS purchase_month,
    CAST(o.purchased_at AS DATE)                      AS purchase_date,
    o.approved_at,
    o.delivered_carrier_at,
    o.delivered_customer_at,
    o.estimated_delivery_at,

    -- Items (NULL where the order has no items: 775 unavailable/canceled orders)
    i.n_items,
    i.n_distinct_products,
    i.n_sellers,
    i.items_value,
    i.freight_value,
    i.items_plus_freight,

    -- Payments (NULL for the 1 order with no payment record)
    p.payments_value,
    p.n_payment_lines,
    p.dominant_payment_type,
    p.max_installments,

    -- Reviews (NULL for the 768 orders never reviewed)
    r.review_score,
    r.review_created_at,
    r.n_reviews          AS n_reviews_collapsed,
    r.score_spread       AS review_score_spread,
    r.has_comment        AS review_has_comment,
    r.answer_lag_days    AS review_answer_lag_days,

    -- Durations, all at date granularity
    date_diff('day', CAST(o.purchased_at AS DATE),
                     CAST(o.delivered_customer_at AS DATE)) AS delivery_days,
    date_diff('day', CAST(o.purchased_at AS DATE),
                     CAST(o.estimated_delivery_at AS DATE)) AS promised_days,
    date_diff('day', CAST(o.purchased_at AS DATE),
                     CAST(o.delivered_carrier_at AS DATE))  AS handover_days,
    date_diff('day', CAST(o.estimated_delivery_at AS DATE),
                     CAST(o.delivered_customer_at AS DATE)) AS delay_days,
        -- delay_days > 0 late, = 0 on the promised day, < 0 early

    -- Flags the KPI layer filters on
    (o.order_status NOT IN ('canceled', 'unavailable'))     AS is_sale_eligible,
    (o.order_status = 'delivered'
     AND o.delivered_customer_at IS NOT NULL
     AND o.estimated_delivery_at IS NOT NULL)               AS has_delivery_measurement,
    (o.order_status = 'delivered'
     AND o.delivered_customer_at IS NOT NULL
     AND o.estimated_delivery_at IS NOT NULL
     AND CAST(o.delivered_customer_at AS DATE)
         > CAST(o.estimated_delivery_at AS DATE))           AS is_late,
    (r.review_score IS NOT NULL)                            AS has_review,
    (i.n_sellers > 1)                                       AS is_multi_seller,
    (o.delivered_customer_at IS NOT NULL
     AND o.delivered_carrier_at IS NOT NULL
     AND o.delivered_customer_at < o.delivered_carrier_at)  AS has_date_anomaly,
    (o.purchased_at >= TIMESTAMP '2017-01-01'
     AND o.purchased_at <  TIMESTAMP '2018-09-01')          AS in_analysis_window
        -- boundary months hold 4, 1, 16 and 4 orders; including them would put
        -- an artificial cliff at each end of every time series

FROM stg.orders o
LEFT JOIN stg.customers        c ON c.customer_id = o.customer_id
LEFT JOIN int.items_by_order   i ON i.order_id    = o.order_id
LEFT JOIN int.payments_by_order p ON p.order_id   = o.order_id
LEFT JOIN int.reviews_by_order r ON r.order_id    = o.order_id
LEFT JOIN stg.geolocation      g ON g.zip_prefix  = c.customer_zip_prefix;
