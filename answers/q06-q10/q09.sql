-- Q9: payments lack a timestamp: 2018 is the order purchase date, not payment date.
-- Means are per payment row; columns distinguish all types from credit-card-only.
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
GROUP BY customer_state ORDER BY customer_state NULLS LAST;

-- Both interpretations of the unspecified period for the overall type breakdown.
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
FROM populations GROUP BY period, payment_type ORDER BY period, payment_type NULLS LAST;
