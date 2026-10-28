-- Named variants are defined in model/55_answers_block_b.sql.
SELECT * FROM mart.q08_status_snapshot ORDER BY orders_count DESC, order_status;
