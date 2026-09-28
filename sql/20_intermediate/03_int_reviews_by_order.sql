-- Collapse multiple reviews to one row per order.
--
-- Rule: keep the most recent review per order (review_created_at, then
-- review_answered_at, then review_id for a stable result). The later review is
-- the customer's settled view after any support contact, which is the one an
-- operational fix would have to move.
--
-- 547 orders have more than one. n_reviews and score_spread are kept so anyone
-- can check how much this rule actually changed.
CREATE OR REPLACE TABLE int.reviews_by_order AS
WITH ranked AS (
    SELECT
        order_id,
        review_id,
        review_score,
        review_created_at,
        review_answered_at,
        has_comment,
        row_number() OVER (
            PARTITION BY order_id
            ORDER BY review_created_at DESC, review_answered_at DESC, review_id
        ) AS rn
    FROM stg.order_reviews
),
agg AS (
    SELECT
        order_id,
        count(*)                              AS n_reviews,
        max(review_score) - min(review_score) AS score_spread,
        avg(review_score)                     AS mean_score_all_reviews
    FROM stg.order_reviews
    GROUP BY order_id
)
SELECT
    r.order_id,
    r.review_id,
    r.review_score,
    r.review_created_at,
    r.review_answered_at,
    r.has_comment,
    a.n_reviews,
    a.score_spread,
    a.mean_score_all_reviews,
    date_diff('day', r.review_created_at, r.review_answered_at) AS answer_lag_days
FROM ranked r
JOIN agg a ON a.order_id = r.order_id
WHERE r.rn = 1;
