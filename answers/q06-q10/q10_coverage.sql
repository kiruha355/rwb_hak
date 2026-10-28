-- Q10 exclusions and overlaps: counts are orders, not review rows.
WITH scores AS (
    SELECT o.order_id, o.is_delivered,
           count(DISTINCT r.review_score) AS distinct_nonnull_scores,
           count(DISTINCT r.review_score) FILTER (WHERE r.review_score BETWEEN 1 AND 5) AS valid_scores,
           count(*) FILTER (WHERE r.review_score IS NOT NULL AND r.review_score NOT BETWEEN 1 AND 5) AS invalid_score_pairs
    FROM mart.v_orders o LEFT JOIN core.fact_review r USING (order_id)
    GROUP BY o.order_id, o.is_delivered
), populations AS (
    SELECT 'all_statuses'::text AS population, * FROM scores
    UNION ALL
    SELECT 'delivered', * FROM scores WHERE is_delivered
)
SELECT population, count(*) AS orders_count,
       count(*) FILTER (WHERE distinct_nonnull_scores = 0) AS orders_without_score,
       count(*) FILTER (WHERE distinct_nonnull_scores > 1) AS orders_with_multiple_scores,
       count(*) FILTER (WHERE valid_scores > 1) AS orders_in_multiple_valid_score_groups,
       count(*) FILTER (WHERE invalid_score_pairs > 0) AS orders_with_out_of_range_score
FROM populations GROUP BY population ORDER BY population;
