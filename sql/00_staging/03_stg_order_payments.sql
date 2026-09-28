-- Grain: 1 row = 1 payment instrument used on an order.
-- Key: (order_id, payment_sequential). An order split across a voucher and a
-- card produces two rows; summing payments alongside items would double-count.
CREATE OR REPLACE TABLE stg.order_payments AS
SELECT
    order_id,
    TRY_CAST(payment_sequential   AS INTEGER)      AS payment_sequential,
    payment_type,
    TRY_CAST(payment_installments AS INTEGER)      AS payment_installments,
    TRY_CAST(payment_value        AS DECIMAL(12,2)) AS payment_value
FROM raw.order_payments;
