-- Named variants are defined in model/55_answers_block_b.sql.
SELECT * FROM mart.q09_payments_2018_by_state ORDER BY customer_state NULLS LAST;

SELECT * FROM mart.q09_payment_methods ORDER BY period, payment_type NULLS LAST;
