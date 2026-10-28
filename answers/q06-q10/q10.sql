-- Q10: orders can have multiple scores. Return both explicit weighting policies.
-- within_score: one order per distinct score, so score groups can overlap.
-- single_score_only: exclude orders with more than one distinct non-NULL score.
WITH order_scores AS (
    SELECT DISTINCT order_id, review_score FROM core.fact_review
    WHERE review_score IS NOT NULL
), score_counts AS (
    SELECT order_id, count(*) AS distinct_score_count FROM order_scores GROUP BY order_id
), associations AS (
    SELECT 'within_score'::text AS score_policy, s.order_id, s.review_score
    FROM order_scores s
    UNION ALL
    SELECT 'single_score_only', s.order_id, s.review_score
    FROM order_scores s JOIN score_counts c USING (order_id)
    WHERE c.distinct_score_count = 1
), grid AS (
    SELECT population, score_policy, late_basis, review_score
    FROM (VALUES ('within_score'), ('single_score_only')) p(score_policy)
    CROSS JOIN (VALUES ('all_statuses'), ('delivered')) pop(population)
    CROSS JOIN (VALUES ('calendar_day'), ('timestamp')) l(late_basis)
    CROSS JOIN generate_series(1, 5) s(review_score)
), measured AS (
    SELECT a.score_policy, a.review_score, d.*
    FROM associations a JOIN mart.v_order_delivery_variants d USING (order_id)
    WHERE a.review_score BETWEEN 1 AND 5
), populations AS (
    SELECT 'all_statuses'::text AS population, m.* FROM measured m
    UNION ALL
    SELECT 'delivered', m.* FROM measured m WHERE m.is_delivered
), alternatives AS (
    SELECT m.*, 'calendar_day'::text AS late_basis, is_late_calendar_day AS is_late FROM populations m
    UNION ALL
    SELECT m.*, 'timestamp', is_late_timestamp FROM populations m
)
SELECT g.population, g.score_policy, g.late_basis, g.review_score, count(a.order_id) AS orders_count,
       count(a.purchase_to_delivery_days) AS duration_denominator,
       avg(a.purchase_to_delivery_days) AS avg_delivery_days,
       count(a.is_late) AS late_denominator,
       count(*) FILTER (WHERE a.is_late) AS late_orders,
       100.0 * count(*) FILTER (WHERE a.is_late) / nullif(count(a.is_late), 0) AS late_pct
FROM grid g LEFT JOIN alternatives a USING (population, score_policy, late_basis, review_score)
GROUP BY g.population, g.score_policy, g.late_basis, g.review_score
ORDER BY g.population, g.score_policy, g.late_basis, g.review_score;
