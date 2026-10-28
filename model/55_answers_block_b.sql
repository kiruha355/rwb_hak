-- Q6–Q10 named variants. Definitions retain the original populations and caveats.
-- All relations are in mart; build.sql executes this stage in its transaction.

-- Q6: purchase calendar date; all statuses and delivered are alternatives.
-- Return every product tied for the maximum number of distinct non-NULL prices.
CREATE VIEW mart.q06_price_history AS
WITH populations AS (
    SELECT 'all_statuses'::text AS population, i.* FROM mart.v_order_items i
    UNION ALL
    SELECT 'delivered', i.* FROM mart.v_order_items i WHERE i.is_delivered
), counts AS (
    SELECT population, product_id, count(DISTINCT price) AS distinct_prices,
           count(*) FILTER (WHERE price IS NULL) AS units_with_unknown_price
    FROM populations GROUP BY population, product_id
), winners AS (
    SELECT *, max(distinct_prices) OVER (PARTITION BY population) AS max_distinct_prices
    FROM counts
)
SELECT p.population, p.product_id, w.distinct_prices, w.units_with_unknown_price,
       p.order_purchase_timestamp::date AS purchase_date, p.price, count(*) AS units_sold
FROM populations p JOIN winners w USING (population, product_id)
WHERE w.distinct_prices = w.max_distinct_prices AND w.distinct_prices > 0
GROUP BY p.population, p.product_id, w.distinct_prices, w.units_with_unknown_price,
         p.order_purchase_timestamp::date, p.price;

-- Q7: threshold applied to orders in each population, not just measured orders.
CREATE VIEW mart.q07_delivery_by_state AS
WITH populations AS (
    SELECT 'all_statuses'::text AS population, o.customer_state, d.*
    FROM mart.v_orders o JOIN mart.v_order_delivery_variants d USING (order_id)
    UNION ALL
    SELECT 'delivered', o.customer_state, d.*
    FROM mart.v_orders o JOIN mart.v_order_delivery_variants d USING (order_id)
    WHERE d.is_delivered
), alternatives AS (
    SELECT p.*, 'calendar_day'::text AS late_basis, is_late_calendar_day AS is_late FROM populations p
    UNION ALL
    SELECT p.*, 'timestamp', is_late_timestamp FROM populations p
)
SELECT population, customer_state, late_basis, count(*) AS orders_count,
       count(purchase_to_delivery_days) AS duration_denominator,
       avg(purchase_to_delivery_days) AS avg_delivery_days,
       count(is_late) AS late_denominator,
       count(*) FILTER (WHERE is_late) AS late_orders,
       100.0 * count(*) FILTER (WHERE is_late) / nullif(count(is_late), 0) AS late_pct
FROM alternatives GROUP BY population, customer_state, late_basis;

-- Q8: snapshot statuses, not transitions; denominator includes every order.
CREATE VIEW mart.q08_status_snapshot AS
WITH counts AS (
    SELECT order_status, count(*) AS orders_count,
           count(*) FILTER (WHERE source_rows_count = 0) AS orders_without_items
    FROM mart.v_orders GROUP BY order_status
)
SELECT order_status, orders_count,
       100.0 * orders_count / nullif(sum(orders_count) OVER (), 0) AS orders_pct,
       orders_without_items
FROM counts;

-- Q9: payments lack a timestamp: 2018 is the order purchase date, not payment date.
-- Means are per payment row; columns distinguish all types from credit-card-only.
CREATE VIEW mart.q09_payments_2018_by_state AS
WITH payments AS (
    SELECT p.*, o.customer_state, o.order_purchase_timestamp
    FROM core.fact_payment p JOIN core.fact_order o USING (order_id)
)
SELECT customer_state, count(*) AS payment_count,
       count(payment_value) AS amount_denominator,
       CASE WHEN count(payment_value) = count(*) THEN sum(payment_value) END AS payment_amount,
       sum(payment_value) AS known_payment_amount_sum,
       count(payment_installments) AS installments_denominator,
       avg(payment_installments::numeric) AS avg_installments_all_types,
       count(payment_installments) FILTER (WHERE payment_type = 'credit_card') AS credit_installments_denominator,
       avg(payment_installments::numeric) FILTER (WHERE payment_type = 'credit_card') AS avg_installments_credit_card
FROM payments
WHERE order_purchase_timestamp >= timestamp '2018-01-01'
  AND order_purchase_timestamp < timestamp '2019-01-01'
GROUP BY customer_state;

-- Both interpretations of the unspecified period for the overall type breakdown.
CREATE VIEW mart.q09_payment_methods AS
WITH payments AS (
    SELECT p.*, o.order_purchase_timestamp
    FROM core.fact_payment p JOIN core.fact_order o USING (order_id)
), populations AS (
    SELECT 'all_snapshot'::text AS period, * FROM payments
    UNION ALL
    SELECT 'purchase_2018', * FROM payments
    WHERE order_purchase_timestamp >= timestamp '2018-01-01'
      AND order_purchase_timestamp < timestamp '2019-01-01'
)
SELECT period, payment_type, count(*) AS payment_count,
       count(payment_installments) AS installments_denominator,
       avg(payment_installments::numeric) AS avg_installments
FROM populations GROUP BY period, payment_type;

-- Q10: orders can have multiple scores. Return both explicit weighting policies.
-- within_score: one order per distinct score, so score groups can overlap.
-- single_score_only: exclude orders with more than one distinct non-NULL score.
CREATE VIEW mart.q10_review_delivery AS
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
GROUP BY g.population, g.score_policy, g.late_basis, g.review_score;

-- Q10 exclusions and overlaps: counts are orders, not review rows.
CREATE VIEW mart.q10_review_coverage AS
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
FROM populations GROUP BY population;
