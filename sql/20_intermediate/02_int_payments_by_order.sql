-- Collapse split payments to one row per order.
-- 103,886 payment rows -> 99,440 order rows (one order has no payment record).
-- 'Dominant' payment type = the instrument that carried the largest amount;
-- ties broken alphabetically so the result is deterministic across rebuilds.
CREATE OR REPLACE TABLE int.payments_by_order AS
WITH ranked AS (
    SELECT
        order_id,
        payment_type,
        sum(payment_value) AS value_by_type,
        row_number() OVER (
            PARTITION BY order_id
            ORDER BY sum(payment_value) DESC, payment_type
        ) AS rn
    FROM stg.order_payments
    GROUP BY order_id, payment_type
)
SELECT
    p.order_id,
    count(*)                        AS n_payment_lines,
    count(DISTINCT p.payment_type)  AS n_payment_types,
    sum(p.payment_value)            AS payments_value,   -- cash collected, NOT merchandise value
    max(p.payment_installments)     AS max_installments,
    any_value(r.payment_type)       AS dominant_payment_type
FROM stg.order_payments p
JOIN ranked r ON r.order_id = p.order_id AND r.rn = 1
GROUP BY p.order_id;
