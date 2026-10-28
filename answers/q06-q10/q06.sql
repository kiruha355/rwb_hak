-- Named variants are defined in model/55_answers_block_b.sql.
SELECT * FROM mart.q06_price_history ORDER BY population, product_id, purchase_date NULLS LAST, price NULLS LAST;
