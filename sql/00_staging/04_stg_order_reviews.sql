-- Grain: 1 row = 1 review. Key: review_id (uniqueness verified in 10_quality).
-- order_id is NOT unique here: some orders carry more than one review.
-- Collapsing to one review per order happens in 20_intermediate, with the
-- rule stated there and the number of collapsed rows reported.
CREATE OR REPLACE TABLE stg.order_reviews AS
SELECT
    review_id,
    order_id,
    TRY_CAST(review_score AS SMALLINT)              AS review_score,
    review_comment_title,
    review_comment_message,
    TRY_CAST(review_creation_date    AS TIMESTAMP)  AS review_created_at,
    TRY_CAST(review_answer_timestamp AS TIMESTAMP)  AS review_answered_at,
    -- Text is not analysed (no NLP in scope); presence is, as a coverage metric.
    (review_comment_message IS NOT NULL
     AND trim(review_comment_message) <> '')        AS has_comment
FROM raw.order_reviews;
