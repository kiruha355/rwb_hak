-- Named variants are defined in model/55_answers_block_b.sql.
SELECT * FROM mart.q07_delivery_by_state WHERE orders_count >= 500::bigint ORDER BY population, customer_state NULLS LAST, late_basis;
