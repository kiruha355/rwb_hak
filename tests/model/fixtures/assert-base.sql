-- Raises cannot be disabled by plpgsql.check_asserts. Fixture constants only.
DO $fixture$
DECLARE n bigint; r record;
BEGIN
 SELECT count(*) INTO n FROM raw.order_items i JOIN raw.order_payments p USING(order_id)
 JOIN raw.order_reviews v USING(order_id) WHERE order_id='fanout';
 IF n<>12 THEN RAISE EXCEPTION 'Broken 2 items x 3 payments x 2 reviews fixture: %',n; END IF;
 SELECT * INTO STRICT r FROM mart.v_orders WHERE order_id='fanout';
 IF ROW(r.source_rows_count,r.payments_count,r.review_pairs_count,r.item_revenue,r.freight_amount,r.order_gmv,r.payment_amount)
 IS DISTINCT FROM ROW(2::bigint,3::bigint,2::bigint,30::numeric,3::numeric,33::numeric,30::numeric)
 THEN RAISE EXCEPTION 'Fanout or wrong order aggregates: %',to_jsonb(r); END IF;
 SELECT * INTO STRICT r FROM mart.v_orders WHERE order_id='neither';
 IF r.payment_coverage IS DISTINCT FROM 'neither' OR r.source_rows_count<>0 OR r.payments_count<>0
 OR r.item_revenue IS NOT NULL OR r.order_gmv IS NOT NULL OR r.payment_amount IS NOT NULL
 THEN RAISE EXCEPTION 'No-child unknowns collapsed or order lost'; END IF;
 SELECT * INTO STRICT r FROM mart.v_orders WHERE order_id='all-null';
 IF r.payment_coverage IS DISTINCT FROM 'both' OR r.source_rows_count<>1 OR r.payments_count<>1
 OR r.price_valid_count<>0 OR r.payment_valid_count<>0 OR r.order_gmv IS NOT NULL OR r.payment_amount IS NOT NULL
 THEN RAISE EXCEPTION 'All-NULL children mistaken for no children or known zero'; END IF;
 SELECT * INTO STRICT r FROM mart.v_orders WHERE order_id='known-zero';
 IF r.order_gmv IS DISTINCT FROM 0::numeric OR r.payment_amount IS DISTINCT FROM 0::numeric
 OR r.price_valid_count<>1 OR r.payment_valid_count<>1 THEN RAISE EXCEPTION 'Known zero lost'; END IF;
 SELECT * INTO STRICT r FROM mart.v_orders WHERE order_id='partial';
 IF r.item_revenue IS DISTINCT FROM 12::numeric OR r.order_gmv IS NOT NULL
 OR r.item_components_valid_count<>1 THEN RAISE EXCEPTION 'Partial components presented as complete'; END IF;
 IF (SELECT payment_coverage FROM mart.v_orders WHERE order_id='items-only') IS DISTINCT FROM 'items_only'
 OR (SELECT payment_coverage FROM mart.v_orders WHERE order_id='payments-only') IS DISTINCT FROM 'payments_only'
 THEN RAISE EXCEPTION 'One-sided payment coverage lost'; END IF;
 IF EXISTS(SELECT FROM mart.v_order_payment_reconciliation WHERE order_id IN ('neither','all-null','partial','items-only','payments-only')
 AND (is_comparable OR payment_delta IS NOT NULL OR delta_nonzero_exact IS NOT NULL))
 THEN RAISE EXCEPTION 'Unknown comparison collapsed to measured reconciliation'; END IF;
 SELECT * INTO STRICT r FROM mart.v_order_delivery_variants WHERE order_id='late-null';
 IF r.is_late_calendar_day IS NOT NULL OR r.is_late_timestamp IS NOT NULL
 OR r.is_handover_after_min_item_deadline IS NOT NULL OR r.is_handover_after_max_item_deadline IS NOT NULL
 THEN RAISE EXCEPTION 'NULL late/deadline comparison became false or zero'; END IF;
 SELECT * INTO STRICT r FROM mart.v_order_delivery_variants WHERE order_id='fanout';
 IF r.is_late_calendar_day IS DISTINCT FROM false OR r.is_late_timestamp IS DISTINCT FROM true
 OR r.is_handover_after_min_item_deadline IS DISTINCT FROM true OR r.is_handover_after_max_item_deadline IS DISTINCT FROM false
 THEN RAISE EXCEPTION 'Named day/timestamp/min/max variants collapsed'; END IF;
 IF (SELECT count(*) FROM core.fact_review WHERE review_id='shared-review')<>2
 OR NOT EXISTS(SELECT FROM core.fact_review WHERE review_id='second-review' AND review_comment_title='' AND review_answer_timestamp IS NULL)
 THEN RAISE EXCEPTION 'Review pairs, empty text or NULL payload lost'; END IF;
 IF NOT EXISTS(SELECT FROM core.dim_category WHERE category_key='unknown' AND is_unknown AND name_en IS NULL)
 OR NOT EXISTS(SELECT FROM core.dim_category WHERE category_key='pt:pc_gamer' AND NOT is_unknown AND NOT is_translated)
 OR NOT EXISTS(SELECT FROM core.dim_category WHERE category_key='pt:unused')
 OR NOT EXISTS(SELECT FROM core.dim_customer_context WHERE customer_id='unused-context')
 THEN RAISE EXCEPTION 'Category states, unused translation or unused context lost'; END IF;
END
$fixture$;
