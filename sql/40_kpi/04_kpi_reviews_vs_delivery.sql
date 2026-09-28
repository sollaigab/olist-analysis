-- Q3: how do reviews differ between on-time and late orders?
--
-- CAUSATION WARNING, kept in the code so it travels with the numbers:
-- these views show an ASSOCIATION. Late orders and low scores co-occur, but
-- the same underlying problem (a difficult route, a slow seller, an
-- out-of-stock item) can produce both. Nothing here isolates a causal effect.
--
-- Group sizes are columns, not footnotes, so no comparison can be quoted
-- without its n.
CREATE OR REPLACE VIEW mart.kpi_reviews_by_punctuality AS
SELECT
    CASE WHEN is_late THEN 'late' ELSE 'on time' END AS delivery_outcome,
    count(*)                                         AS n_orders,
    round(avg(review_score), 3)                      AS mean_review_score,
    median(review_score)                             AS median_review_score,
    count(*) FILTER (WHERE review_score <= 2)        AS n_low_scores,
    round(100.0 * count(*) FILTER (WHERE review_score <= 2) / count(*), 2) AS pct_1_2_star,
    count(*) FILTER (WHERE review_score = 5)         AS n_five_star,
    round(100.0 * count(*) FILTER (WHERE review_score = 5) / count(*), 2)  AS pct_5_star,
    round(100.0 * count(*) FILTER (WHERE review_has_comment) / count(*), 2) AS pct_with_comment
FROM mart.fct_orders
WHERE has_delivery_measurement AND has_review AND in_analysis_window
GROUP BY 1
ORDER BY 1;

-- Same association, resolved by how late the order actually was. Buckets are
-- reported with their n so the thin tails are visibly thin.
CREATE OR REPLACE VIEW mart.kpi_reviews_by_delay_bucket AS
WITH bucketed AS (
    SELECT
        CASE
            WHEN delay_days <= -8 THEN '1. early by 8+ days'
            WHEN delay_days <  0  THEN '2. early by 1-7 days'
            WHEN delay_days =  0  THEN '3. on the promised day'
            WHEN delay_days <= 3  THEN '4. late 1-3 days'
            WHEN delay_days <= 7  THEN '5. late 4-7 days'
            WHEN delay_days <= 15 THEN '6. late 8-15 days'
            ELSE                       '7. late 16+ days'
        END AS delay_bucket,
        review_score,
        review_has_comment
    FROM mart.fct_orders
    WHERE has_delivery_measurement AND has_review AND in_analysis_window
)
SELECT
    delay_bucket,
    count(*)                                  AS n_orders,
    round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct_of_reviewed_orders,
    round(avg(review_score), 3)               AS mean_review_score,
    count(*) FILTER (WHERE review_score <= 2) AS n_low_scores,
    round(100.0 * count(*) FILTER (WHERE review_score <= 2) / count(*), 2) AS pct_1_2_star,
    round(100.0 * count(*) FILTER (WHERE review_has_comment) / count(*), 2) AS pct_with_comment
FROM bucketed
GROUP BY delay_bucket
ORDER BY delay_bucket;

-- Review coverage is not 100%: scores describe the customers who chose to
-- review. This view exposes the denominator so the selection bias is visible.
CREATE OR REPLACE VIEW mart.kpi_review_coverage AS
SELECT
    purchase_month,
    count(*)                                   AS n_sale_eligible_orders,
    count(*) FILTER (WHERE has_review)         AS n_reviewed,
    round(100.0 * count(*) FILTER (WHERE has_review) / count(*), 2) AS review_coverage_pct,
    round(avg(review_score), 3)                AS mean_review_score
FROM mart.fct_orders
WHERE is_sale_eligible AND in_analysis_window
GROUP BY purchase_month
ORDER BY purchase_month;
