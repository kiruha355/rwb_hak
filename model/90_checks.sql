-- W-11: invariant checks, not answers/control.sql baseline values.
-- PostgreSQL 16. Caller owns transaction and raw locks. No raw DML and no COMMIT.
-- Rollback removes check_results changes; RAISE EXCEPTION DETAIL carries failures to stderr.
CREATE TABLE IF NOT EXISTS core.check_results (
 check_name text PRIMARY KEY, check_group text NOT NULL,
 expected text NOT NULL, actual text NOT NULL, ok boolean NOT NULL,
 severity text NOT NULL CHECK (severity IN ('error','warning')),
 checked_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE OR REPLACE FUNCTION core.run_checks() RETURNS void
LANGUAGE plpgsql AS $checks$
DECLARE
 mapping record;
 rule record;
 rules jsonb := '[]'::jsonb;
 n bigint;
 sample text;
 failures text;
 q text;
 key_null_sql text;
BEGIN
 DELETE FROM core.check_results;
 -- EXCEPT ALL compares typed values with NULL equality and preserves multiplicity.
 -- Key sets alone would miss swapped payloads; counts alone would miss substitutions.
 FOR mapping IN SELECT * FROM (VALUES
 ($sql$orders$sql$, $sql$order_id$sql$,
 $sql$SELECT o.order_id, o.customer_id, c.customer_unique_id, o.order_status,
 o.order_purchase_timestamp::timestamp, o.order_approved_at::timestamp,
 o.order_delivered_carrier_date::timestamp, o.order_delivered_customer_date::timestamp,
 o.order_estimated_delivery_date::timestamp, c.customer_zip_code_prefix,
 CASE WHEN c.customer_zip_code_prefix ~ '^[0-9]{1,5}$' THEN lpad(c.customer_zip_code_prefix,5,'0') END AS customer_zip_code_prefix_validated,
 c.customer_city, c.customer_state
 FROM raw.orders o LEFT JOIN raw.customers c ON c.customer_id=o.customer_id$sql$,
 $sql$SELECT order_id, customer_id, customer_unique_id, order_status,
 order_purchase_timestamp, order_approved_at, order_delivered_carrier_date,
 order_delivered_customer_date, order_estimated_delivery_date,
 customer_zip_code_prefix, customer_zip_code_prefix_validated, customer_city, customer_state
 FROM core.fact_order$sql$),
 ($sql$items$sql$, $sql$order_id, order_item_id$sql$,
 $sql$SELECT order_id, order_item_id::integer, product_id, seller_id,
 price::numeric, freight_value::numeric, shipping_limit_date::timestamp AS shipping_limit_at
 FROM raw.order_items$sql$,
 $sql$SELECT order_id, order_item_id, product_id, seller_id, price, freight_value,
 shipping_limit_at FROM core.fact_order_item$sql$),
 ($sql$payments$sql$, $sql$order_id, payment_sequential$sql$,
 $sql$SELECT order_id, payment_sequential::integer, payment_type,
 payment_installments::integer, payment_value::numeric FROM raw.order_payments$sql$,
 $sql$SELECT order_id, payment_sequential, payment_type, payment_installments, payment_value
 FROM core.fact_payment$sql$),
 ($sql$reviews$sql$, $sql$review_id, order_id$sql$,
 $sql$SELECT review_id, order_id, review_score::integer, review_comment_title,
 review_comment_message, review_creation_date::timestamp, review_answer_timestamp::timestamp
 FROM raw.order_reviews$sql$,
 $sql$SELECT review_id, order_id, review_score, review_comment_title,
 review_comment_message, review_creation_date, review_answer_timestamp FROM core.fact_review$sql$),
 ($sql$products$sql$, $sql$product_id$sql$,
 $sql$SELECT product_id, product_category_name,
 product_name_lenght::integer, product_description_lenght::integer, product_photos_qty::integer,
 product_weight_g::numeric, product_length_cm::numeric, product_height_cm::numeric,
 product_width_cm::numeric FROM raw.products$sql$,
 $sql$SELECT p.product_id, c.name_pt AS product_category_name, product_name_lenght,
 product_description_lenght, product_photos_qty, product_weight_g, product_length_cm,
 product_height_cm, product_width_cm FROM core.dim_product p
 LEFT JOIN core.dim_category c ON c.category_key=p.category_key$sql$),
 ($sql$sellers$sql$, $sql$seller_id$sql$,
 $sql$SELECT seller_id, seller_zip_code_prefix,
 CASE WHEN seller_zip_code_prefix ~ '^[0-9]{1,5}$' THEN lpad(seller_zip_code_prefix,5,'0') END AS seller_zip_code_prefix_validated,
 seller_city, seller_state FROM raw.sellers$sql$,
 $sql$SELECT seller_id, seller_zip_code_prefix, seller_zip_code_prefix_validated,
 seller_city, seller_state FROM core.dim_seller$sql$),
 ($sql$customer_contexts$sql$, $sql$customer_id$sql$,
 $sql$SELECT customer_id, customer_unique_id, customer_zip_code_prefix,
 CASE WHEN customer_zip_code_prefix ~ '^[0-9]{1,5}$' THEN lpad(customer_zip_code_prefix,5,'0') END AS customer_zip_code_prefix_validated,
 customer_city, customer_state FROM raw.customers$sql$,
 $sql$SELECT customer_id, customer_unique_id, customer_zip_code_prefix,
 customer_zip_code_prefix_validated, customer_city, customer_state FROM core.dim_customer_context$sql$),
 ($sql$translations$sql$, $sql$category_key$sql$,
 $sql$SELECT 'pt:'||product_category_name AS category_key, product_category_name, product_category_name_english FROM raw.product_category_translation$sql$,
 $sql$SELECT category_key, name_pt AS product_category_name, name_en AS product_category_name_english
 FROM core.dim_category WHERE name_pt IN (SELECT product_category_name FROM raw.product_category_translation)$sql$),
 ($sql$buyers$sql$, $sql$customer_unique_id$sql$,
 $sql$SELECT DISTINCT customer_unique_id FROM raw.customers$sql$,
 $sql$SELECT customer_unique_id FROM core.dim_customer$sql$),
 ($sql$categories$sql$, $sql$category_key$sql$,
 $sql$SELECT 'unknown'::text AS category_key, NULL::text AS name_pt,
 NULL::text AS name_en, true AS is_unknown, false AS is_translated
 UNION ALL
 SELECT 'pt:'||n.product_category_name, n.product_category_name, t.product_category_name_english,
 false, t.product_category_name_english IS NOT NULL
 FROM (SELECT product_category_name FROM raw.products WHERE product_category_name IS NOT NULL
       UNION SELECT product_category_name FROM raw.product_category_translation WHERE product_category_name IS NOT NULL) n
 LEFT JOIN raw.product_category_translation t USING(product_category_name)$sql$,
 $sql$SELECT category_key, name_pt, name_en, is_unknown, is_translated FROM core.dim_category$sql$),
 ($sql$statuses$sql$, $sql$order_status$sql$,
 $sql$SELECT order_status, order_status='delivered' AS is_revenue FROM (
 SELECT order_status FROM raw.orders WHERE order_status IS NOT NULL
 UNION SELECT unnest(ARRAY['delivered','shipped','canceled','unavailable','invoiced','processing','created','approved'])) s$sql$,
 $sql$SELECT order_status, is_revenue FROM core.dim_order_status$sql$),
 ($sql$calendar$sql$, $sql$date_day$sql$,
 $sql$WITH source_dates AS (SELECT order_purchase_timestamp::timestamp::date AS d FROM raw.orders
 UNION ALL SELECT order_approved_at::timestamp::date FROM raw.orders
 UNION ALL SELECT order_delivered_carrier_date::timestamp::date FROM raw.orders
 UNION ALL SELECT order_delivered_customer_date::timestamp::date FROM raw.orders
 UNION ALL SELECT order_estimated_delivery_date::timestamp::date FROM raw.orders
 UNION ALL SELECT shipping_limit_date::timestamp::date FROM raw.order_items
 UNION ALL SELECT review_creation_date::timestamp::date FROM raw.order_reviews
 UNION ALL SELECT review_answer_timestamp::timestamp::date FROM raw.order_reviews), bounds AS (
 SELECT least(min(d),DATE '2016-09-01') AS lo, greatest(max(d),DATE '2018-08-31') AS hi FROM source_dates),
 days AS (SELECT lo+i AS date_day FROM bounds CROSS JOIN LATERAL generate_series(0,hi-lo) i)
 SELECT date_day, date_trunc('month',date_day)::date AS month_start,
 extract(year FROM date_day)::integer AS year_number,
 extract(quarter FROM date_day)::integer AS quarter_number,
 extract(month FROM date_day)::integer AS month_number,
 extract(day FROM date_day)::integer AS day_of_month,
 extract(isoyear FROM date_day)::integer AS iso_year,
 extract(week FROM date_day)::integer AS iso_week,
 extract(isodow FROM date_day)::integer AS iso_day_of_week,
 extract(isodow FROM date_day) IN (6,7) AS is_weekend FROM days$sql$,
 $sql$WITH source_dates AS (SELECT order_purchase_timestamp::timestamp::date AS d FROM raw.orders
 UNION ALL SELECT order_approved_at::timestamp::date FROM raw.orders
 UNION ALL SELECT order_delivered_carrier_date::timestamp::date FROM raw.orders
 UNION ALL SELECT order_delivered_customer_date::timestamp::date FROM raw.orders
 UNION ALL SELECT order_estimated_delivery_date::timestamp::date FROM raw.orders
 UNION ALL SELECT shipping_limit_date::timestamp::date FROM raw.order_items
 UNION ALL SELECT review_creation_date::timestamp::date FROM raw.order_reviews
 UNION ALL SELECT review_answer_timestamp::timestamp::date FROM raw.order_reviews), bounds AS (
 SELECT least(min(d),DATE '2016-09-01') AS lo, greatest(max(d),DATE '2018-08-31') AS hi FROM source_dates)
 SELECT date_day, month_start, year_number, quarter_number, month_number, day_of_month,
 iso_year, iso_week, iso_day_of_week, is_weekend FROM core.dim_date CROSS JOIN bounds WHERE date_day BETWEEN lo AND hi$sql$),
 ($sql$order_mart$sql$, $sql$order_id$sql$,
 $sql$WITH i AS (
 SELECT order_id,count(*) AS n,count(price) AS price_n,count(freight_value) AS freight_n,
 count(*) FILTER (WHERE price IS NOT NULL AND freight_value IS NOT NULL) AS component_n,
 sum(price::numeric) AS price_sum,sum(freight_value::numeric) AS freight_sum,
 sum(price::numeric+freight_value::numeric) AS gmv_sum FROM raw.order_items GROUP BY order_id),
 p AS (SELECT order_id,count(*) AS n,count(payment_value) AS value_n,sum(payment_value::numeric) AS value_sum
 FROM raw.order_payments GROUP BY order_id),
 r AS (SELECT order_id,count(*) AS n FROM raw.order_reviews GROUP BY order_id)
 SELECT o.order_id,coalesce(i.n,0) AS source_rows_count,coalesce(p.n,0) AS payments_count,
 coalesce(r.n,0) AS review_pairs_count,coalesce(i.price_n,0) AS price_valid_count,
 coalesce(i.freight_n,0) AS freight_valid_count,coalesce(i.component_n,0) AS item_components_valid_count,
 coalesce(p.value_n,0) AS payment_valid_count,
 CASE WHEN i.price_n=i.n THEN i.price_sum END AS item_revenue,
 CASE WHEN i.freight_n=i.n THEN i.freight_sum END AS freight_amount,
 CASE WHEN i.component_n=i.n THEN i.gmv_sum END AS order_gmv,
 CASE WHEN p.value_n=p.n THEN p.value_sum END AS payment_amount,
 CASE WHEN i.n IS NOT NULL AND p.n IS NOT NULL THEN 'both' WHEN i.n IS NOT NULL THEN 'items_only'
 WHEN p.n IS NOT NULL THEN 'payments_only' ELSE 'neither' END AS payment_coverage
 FROM raw.orders o LEFT JOIN i USING(order_id) LEFT JOIN p USING(order_id) LEFT JOIN r USING(order_id)$sql$,
 $sql$SELECT order_id,source_rows_count,payments_count,review_pairs_count,price_valid_count,
 freight_valid_count,item_components_valid_count,payment_valid_count,item_revenue,freight_amount,
 order_gmv,payment_amount,payment_coverage FROM mart.v_orders$sql$),
 ($sql$orders_without_order_items$sql$, $sql$order_id$sql$,
 $sql$SELECT order_id FROM raw.orders o WHERE NOT EXISTS (SELECT FROM raw.order_items c WHERE c.order_id=o.order_id)$sql$,
 $sql$SELECT order_id FROM core.fact_order o WHERE NOT EXISTS (SELECT FROM core.fact_order_item c WHERE c.order_id=o.order_id)$sql$),
 ($sql$orders_without_order_payments$sql$, $sql$order_id$sql$,
 $sql$SELECT order_id FROM raw.orders o WHERE NOT EXISTS (SELECT FROM raw.order_payments c WHERE c.order_id=o.order_id)$sql$,
 $sql$SELECT order_id FROM core.fact_order o WHERE NOT EXISTS (SELECT FROM core.fact_payment c WHERE c.order_id=o.order_id)$sql$),
 ($sql$orders_without_order_reviews$sql$, $sql$order_id$sql$,
 $sql$SELECT order_id FROM raw.orders o WHERE NOT EXISTS (SELECT FROM raw.order_reviews c WHERE c.order_id=o.order_id)$sql$,
 $sql$SELECT order_id FROM core.fact_order o WHERE NOT EXISTS (SELECT FROM core.fact_review c WHERE c.order_id=o.order_id)$sql$)
 ) AS mappings(name, keys, source_sql, target_sql)
 LOOP
   rules := rules || jsonb_build_array(
     jsonb_build_object('name',mapping.name||'.row_count','group','balance','severity','error',
       'sql',format('SELECT (SELECT count(*) FROM (%s) e) expected, (SELECT count(*) FROM (%s) a) actual WHERE (SELECT count(*) FROM (%s) e)<>(SELECT count(*) FROM (%s) a)',mapping.source_sql,mapping.target_sql,mapping.source_sql,mapping.target_sql)),
     jsonb_build_object('name',mapping.name||'.keys_raw_minus_core','group','key','severity','error',
       'sql',format('SELECT %s FROM (%s) e EXCEPT SELECT %s FROM (%s) a',mapping.keys,mapping.source_sql,mapping.keys,mapping.target_sql)),
     jsonb_build_object('name',mapping.name||'.keys_core_minus_raw','group','key','severity','error',
       'sql',format('SELECT %s FROM (%s) a EXCEPT SELECT %s FROM (%s) e',mapping.keys,mapping.target_sql,mapping.keys,mapping.source_sql)),
     jsonb_build_object('name',mapping.name||'.multiplicity','group','key','severity','error',
       'sql',format('(SELECT %s,count(*) FROM (%s) e GROUP BY %s EXCEPT ALL SELECT %s,count(*) FROM (%s) a GROUP BY %s) UNION ALL (SELECT %s,count(*) FROM (%s) a GROUP BY %s EXCEPT ALL SELECT %s,count(*) FROM (%s) e GROUP BY %s)',mapping.keys,mapping.source_sql,mapping.keys,mapping.keys,mapping.target_sql,mapping.keys,mapping.keys,mapping.target_sql,mapping.keys,mapping.keys,mapping.source_sql,mapping.keys)),
     jsonb_build_object('name',mapping.name||'.values_raw_minus_core','group','field','severity','error',
       'sql',format('(%s) EXCEPT ALL (%s)',mapping.source_sql,mapping.target_sql)),
     jsonb_build_object('name',mapping.name||'.values_core_minus_raw','group','field','severity','error',
       'sql',format('(%s) EXCEPT ALL (%s)',mapping.target_sql,mapping.source_sql)),
     jsonb_build_object('name',mapping.name||'.null_profiles','group','field','severity','error',
       'sql',format('WITH e AS (SELECT f.key, count(*) FILTER (WHERE f.value=''null''::jsonb) FROM (%s) e CROSS JOIN LATERAL jsonb_each(to_jsonb(e)) f GROUP BY f.key), a AS (SELECT f.key, count(*) FILTER (WHERE f.value=''null''::jsonb) FROM (%s) a CROSS JOIN LATERAL jsonb_each(to_jsonb(a)) f GROUP BY f.key) (TABLE e EXCEPT ALL TABLE a) UNION ALL (TABLE a EXCEPT ALL TABLE e)',mapping.source_sql,mapping.target_sql))
   );
   -- Each mapped relation has a natural unique key, including review-order pairs.
   SELECT string_agg(format('%I IS NULL OR %I::text=''''',trim(k),trim(k)),' OR ')
     INTO key_null_sql FROM unnest(string_to_array(mapping.keys,',')) k;
   rules := rules || jsonb_build_array(
     jsonb_build_object('name',mapping.name||'.source_key_unique','group','key','severity','error',
       'sql',format('SELECT %s,count(*) FROM (%s) e GROUP BY %s HAVING count(*)>1',mapping.keys,mapping.source_sql,mapping.keys)),
     jsonb_build_object('name',mapping.name||'.target_key_unique','group','key','severity','error',
       'sql',format('SELECT %s,count(*) FROM (%s) a GROUP BY %s HAVING count(*)>1',mapping.keys,mapping.target_sql,mapping.keys)),
     jsonb_build_object('name',mapping.name||'.source_key_required','group','key','severity','error',
       'sql',format('SELECT %s FROM (%s) e WHERE %s',mapping.keys,mapping.source_sql,key_null_sql)),
     jsonb_build_object('name',mapping.name||'.target_key_required','group','key','severity','error',
       'sql',format('SELECT %s FROM (%s) a WHERE %s',mapping.keys,mapping.target_sql,key_null_sql))
   );
 END LOOP;
 FOR rule IN SELECT * FROM (VALUES
 ($sql$item_money_order$sql$, $sql$money$sql$, $sql$error$sql$,
 $sql$(SELECT order_id, count(*) AS row_count, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM raw.order_items GROUP BY order_id EXCEPT ALL SELECT order_id, count(*) AS row_count, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM core.fact_order_item GROUP BY order_id) UNION ALL (SELECT order_id, count(*) AS row_count, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM core.fact_order_item GROUP BY order_id EXCEPT ALL SELECT order_id, count(*) AS row_count, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM raw.order_items GROUP BY order_id)$sql$),
 ($sql$item_money_seller$sql$, $sql$money$sql$, $sql$error$sql$,
 $sql$(SELECT seller_id, count(*) AS row_count, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM raw.order_items GROUP BY seller_id EXCEPT ALL SELECT seller_id, count(*) AS row_count, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM core.fact_order_item GROUP BY seller_id) UNION ALL (SELECT seller_id, count(*) AS row_count, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM core.fact_order_item GROUP BY seller_id EXCEPT ALL SELECT seller_id, count(*) AS row_count, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM raw.order_items GROUP BY seller_id)$sql$),
 ($sql$payment_money_order$sql$, $sql$money$sql$, $sql$error$sql$,
 $sql$(SELECT order_id, count(*) AS row_count, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM raw.order_payments GROUP BY order_id EXCEPT ALL SELECT order_id, count(*) AS row_count, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM core.fact_payment GROUP BY order_id) UNION ALL (SELECT order_id, count(*) AS row_count, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM core.fact_payment GROUP BY order_id EXCEPT ALL SELECT order_id, count(*) AS row_count, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM raw.order_payments GROUP BY order_id)$sql$),
 ($sql$payment_money_type$sql$, $sql$money$sql$, $sql$error$sql$,
 $sql$(SELECT payment_type, count(*) AS row_count, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM raw.order_payments GROUP BY payment_type EXCEPT ALL SELECT payment_type, count(*) AS row_count, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM core.fact_payment GROUP BY payment_type) UNION ALL (SELECT payment_type, count(*) AS row_count, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM core.fact_payment GROUP BY payment_type EXCEPT ALL SELECT payment_type, count(*) AS row_count, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM raw.order_payments GROUP BY payment_type)$sql$),
 ($sql$fact_order_item.grand_totals$sql$, $sql$money$sql$, $sql$error$sql$,
 $sql$(SELECT count(*) AS rows, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM raw.order_items EXCEPT ALL SELECT count(*) AS rows, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM core.fact_order_item) UNION ALL (SELECT count(*) AS rows, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM core.fact_order_item EXCEPT ALL SELECT count(*) AS rows, sum(price::numeric) AS price_sum, count(price) AS price_known, count(*) FILTER (WHERE price::numeric=0) AS price_zeros, sum(freight_value::numeric) AS freight_value_sum, count(freight_value) AS freight_value_known, count(*) FILTER (WHERE freight_value::numeric=0) AS freight_value_zeros FROM raw.order_items)$sql$),
 ($sql$fact_payment.grand_totals$sql$, $sql$money$sql$, $sql$error$sql$,
 $sql$(SELECT count(*) AS rows, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM raw.order_payments EXCEPT ALL SELECT count(*) AS rows, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM core.fact_payment) UNION ALL (SELECT count(*) AS rows, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM core.fact_payment EXCEPT ALL SELECT count(*) AS rows, sum(payment_value::numeric) AS payment_value_sum, count(payment_value) AS payment_value_known, count(*) FILTER (WHERE payment_value::numeric=0) AS payment_value_zeros FROM raw.order_payments)$sql$),
 ($sql$fk.order_customer_context$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.fact_order c WHERE NOT EXISTS (SELECT FROM core.dim_customer_context p WHERE p.customer_id=c.customer_id AND p.customer_unique_id=c.customer_unique_id)$sql$),
 ($sql$fk.order_buyer$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.fact_order c WHERE NOT EXISTS (SELECT FROM core.dim_customer p WHERE p.customer_unique_id=c.customer_unique_id)$sql$),
 ($sql$fk.context_buyer$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.dim_customer_context c WHERE NOT EXISTS (SELECT FROM core.dim_customer p WHERE p.customer_unique_id=c.customer_unique_id)$sql$),
 ($sql$fk.order_status$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.fact_order c WHERE NOT EXISTS (SELECT FROM core.dim_order_status p WHERE p.order_status=c.order_status)$sql$),
 ($sql$fk.item_order$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.fact_order_item c WHERE NOT EXISTS (SELECT FROM core.fact_order p WHERE p.order_id=c.order_id)$sql$),
 ($sql$fk.item_product$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.fact_order_item c WHERE NOT EXISTS (SELECT FROM core.dim_product p WHERE p.product_id=c.product_id)$sql$),
 ($sql$fk.item_seller$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.fact_order_item c WHERE NOT EXISTS (SELECT FROM core.dim_seller p WHERE p.seller_id=c.seller_id)$sql$),
 ($sql$fk.payment_order$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.fact_payment c WHERE NOT EXISTS (SELECT FROM core.fact_order p WHERE p.order_id=c.order_id)$sql$),
 ($sql$fk.review_order$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.fact_review c WHERE NOT EXISTS (SELECT FROM core.fact_order p WHERE p.order_id=c.order_id)$sql$),
 ($sql$fk.product_category$sql$, $sql$fk$sql$, $sql$error$sql$,
 $sql$SELECT to_jsonb(c) AS child FROM core.dim_product c WHERE NOT EXISTS (SELECT FROM core.dim_category p WHERE p.category_key=c.category_key)$sql$),
 ($sql$category.product_mapping$sql$, $sql$coverage$sql$, $sql$error$sql$,
 $sql$SELECT p.product_id FROM raw.products p LEFT JOIN core.dim_product c USING(product_id)
 WHERE c.category_key IS DISTINCT FROM CASE WHEN p.product_category_name IS NULL THEN 'unknown' ELSE 'pt:'||p.product_category_name END$sql$),
 ($sql$calendar.gaps$sql$, $sql$calendar$sql$, $sql$error$sql$,
 $sql$SELECT date_day, previous_day FROM (
 SELECT date_day, lag(date_day) OVER (ORDER BY date_day) previous_day FROM core.dim_date) d
 WHERE previous_day IS NOT NULL AND date_day-previous_day<>1$sql$),
 ($sql$calendar.attributes$sql$, $sql$calendar$sql$, $sql$error$sql$,
 $sql$SELECT date_day FROM core.dim_date
 WHERE ROW(month_start,year_number,quarter_number,month_number,day_of_month,iso_year,iso_week,iso_day_of_week,is_weekend)
 IS DISTINCT FROM ROW(date_trunc('month',date_day)::date,extract(year FROM date_day)::integer,
 extract(quarter FROM date_day)::integer,extract(month FROM date_day)::integer,extract(day FROM date_day)::integer,
 extract(isoyear FROM date_day)::integer,extract(week FROM date_day)::integer,extract(isodow FROM date_day)::integer,
 extract(isodow FROM date_day) IN(6,7))$sql$),
 ($sql$numeric.finite$sql$, $sql$typing$sql$, $sql$error$sql$,
 $sql$SELECT 'item' AS grain, order_id, price::text AS value FROM core.fact_order_item WHERE price::text IN ('NaN','Infinity','-Infinity')
 UNION ALL SELECT 'freight',order_id,freight_value::text FROM core.fact_order_item WHERE freight_value::text IN ('NaN','Infinity','-Infinity')
 UNION ALL SELECT 'payment',order_id,payment_value::text FROM core.fact_payment WHERE payment_value::text IN ('NaN','Infinity','-Infinity')
 UNION ALL SELECT 'product',product_id,v::text FROM core.dim_product CROSS JOIN LATERAL
 (VALUES(product_weight_g),(product_length_cm),(product_height_cm),(product_width_cm)) n(v) WHERE v::text IN ('NaN','Infinity','-Infinity')$sql$),
 ($sql$review.payload_fd$sql$, $sql$fd$sql$, $sql$warning$sql$,
 $sql$SELECT review_id, count(*) AS payload_variants FROM (
 SELECT DISTINCT review_id, review_score, review_comment_title, review_comment_message,
 review_creation_date, review_answer_timestamp FROM core.fact_review) p GROUP BY review_id HAVING count(*)>1$sql$),
 ($sql$status.unexpected$sql$, $sql$quality$sql$, $sql$warning$sql$,
 $sql$SELECT DISTINCT order_status FROM core.fact_order WHERE order_status NOT IN
 ('delivered','shipped','canceled','unavailable','invoiced','processing','created','approved')$sql$),
 ($sql$review.score_unusual$sql$, $sql$quality$sql$, $sql$warning$sql$,
 $sql$SELECT review_id, order_id, review_score FROM core.fact_review WHERE review_score NOT BETWEEN 1 AND 5 OR review_score IS NULL$sql$),
 ($sql$order.date_anomalies$sql$, $sql$quality$sql$, $sql$warning$sql$,
 $sql$SELECT order_id FROM core.fact_order WHERE
 order_delivered_carrier_date<order_purchase_timestamp OR order_delivered_customer_date<order_delivered_carrier_date OR
 (order_status='delivered' AND (order_delivered_customer_date IS NULL OR order_approved_at IS NULL)) OR
 (order_status<>'delivered' AND order_delivered_customer_date IS NOT NULL)$sql$),
 ($sql$item_money_category$sql$, $sql$money$sql$, $sql$error$sql$,
 $sql$(SELECT CASE WHEN p.product_category_name IS NULL THEN 'unknown' ELSE 'pt:'||p.product_category_name END AS category_key,
 count(*) AS n, count(i.price) AS known, sum(i.price::numeric) AS money_sum
 FROM raw.order_items i JOIN raw.products p USING(product_id) GROUP BY 1 EXCEPT ALL SELECT p.category_key,count(*) AS n,count(i.price) AS known,sum(i.price) AS money_sum
 FROM core.fact_order_item i JOIN core.dim_product p USING(product_id) GROUP BY 1) UNION ALL (SELECT p.category_key,count(*) AS n,count(i.price) AS known,sum(i.price) AS money_sum
 FROM core.fact_order_item i JOIN core.dim_product p USING(product_id) GROUP BY 1 EXCEPT ALL SELECT CASE WHEN p.product_category_name IS NULL THEN 'unknown' ELSE 'pt:'||p.product_category_name END AS category_key,
 count(*) AS n, count(i.price) AS known, sum(i.price::numeric) AS money_sum
 FROM raw.order_items i JOIN raw.products p USING(product_id) GROUP BY 1)$sql$)
 ) AS additional(name, check_group, severity, query)
 LOOP
   rules := rules || jsonb_build_array(jsonb_build_object('name',rule.name,
     'group',rule.check_group,'severity',rule.severity,'sql',rule.query));
 END LOOP;
 FOR rule IN SELECT * FROM jsonb_to_recordset(rules)
   AS r(name text, "group" text, severity text, sql text)
 LOOP
   BEGIN
     EXECUTE format('SELECT count(*) FROM (%s) violations',rule.sql) INTO n;
     sample := NULL;
     IF n>0 THEN
       EXECUTE format('SELECT left(string_agg(to_jsonb(v)::text, E''\n''),1500) FROM (SELECT * FROM (%s) violations ORDER BY to_jsonb(violations)::text LIMIT 3) v',rule.sql) INTO sample;
     END IF;
     INSERT INTO core.check_results(check_name,check_group,expected,actual,ok,severity)
       VALUES(rule.name,rule."group",'0 violating rows',n::text||coalesce(E'\n'||sample,''),n=0,rule.severity);
   EXCEPTION WHEN OTHERS THEN
     -- A broken check is a failing error, including when the original rule was a warning.
     INSERT INTO core.check_results(check_name,check_group,expected,actual,ok,severity)
       VALUES(rule.name,rule."group",'query executes; 0 violating rows',
         'SQLSTATE '||SQLSTATE||': '||SQLERRM,false,'error');
   END;
 END LOOP;
 SELECT string_agg(check_name||': '||actual,E'\n' ORDER BY check_name) INTO failures
   FROM core.check_results WHERE NOT ok AND severity='error';
 IF failures IS NOT NULL THEN
   RAISE EXCEPTION USING ERRCODE='23514', MESSAGE='core invariant checks failed',
     DETAIL=failures, HINT='Transaction must roll back; preserve this error text because check_results rolls back too.';
 END IF;
 SELECT string_agg(check_name||': '||actual,E'\n' ORDER BY check_name) INTO failures
   FROM core.check_results WHERE NOT ok AND severity='warning';
 IF failures IS NOT NULL THEN
   RAISE WARNING USING MESSAGE='core quality warnings (source values preserved)',DETAIL=failures;
 END IF;
END;
$checks$;

SELECT core.run_checks();
