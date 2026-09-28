-- Collapse multiple reviews to one row per order.
--
-- RULE (stated because any choice here changes the numbers):
--   Keep the MOST RECENT review per order, by review_created_at, breaking ties
--   on review_answered_at and finally on review_id so the result is stable.
--   Rationale: the latest review is the customer's settled opinion after any
--   resolution attempt, which is the opinion an operational fix should move.
--
-- 547 orders carry more than one review; n_reviews records how many rows were
-- collapsed, and score_spread records whether the collapsed reviews disagreed,
-- so the choice of rule can be audited rather than trusted.
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
