-- Generic invariants only. Fixture/pinned answer constants live under tests/.
CREATE OR REPLACE FUNCTION history.check_model() RETURNS void
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
DECLARE chosen text;
BEGIN
    SELECT release_id INTO STRICT chosen FROM core.model_release;
    PERFORM history.assert_release(chosen);
    IF EXISTS (SELECT FROM core.fact_order_item i
        LEFT JOIN history.report_binding b ON b.release_id=chosen
            AND b.order_id=i.order_id AND b.order_item_id=i.order_item_id
        LEFT JOIN core.dim_category_version v ON v.version_id=i.category_version_id
        WHERE b.version_id IS DISTINCT FROM i.category_version_id
           OR ROW(v.product_id,v.category_key,v.attribution_basis,v.event_id,v.baseline_id)
              IS DISTINCT FROM ROW(b.product_id,b.category_key,b.attribution_basis,b.event_id,b.baseline_id)
           OR (v.seller_id IS NOT NULL AND v.seller_id<>i.seller_id))
    THEN RAISE EXCEPTION 'Model category binding mismatch'; END IF;
    IF (SELECT count(*) FROM mart.v_order_items) <> (SELECT count(*) FROM core.fact_order_item)
       OR EXISTS (
        (SELECT b.category_key,count(*) AS n,count(i.price) AS known,sum(i.price) AS amount
         FROM core.fact_order_item i JOIN core.fact_order o USING(order_id)
         JOIN core.dim_order_status s USING(order_status)
         JOIN history.report_binding b ON b.release_id=chosen AND b.order_id=i.order_id AND b.order_item_id=i.order_item_id
         WHERE s.is_revenue GROUP BY b.category_key
         EXCEPT ALL SELECT category_key,count(*),count(price),sum(price) FROM mart.v_order_items WHERE is_revenue GROUP BY category_key)
        UNION ALL
        (SELECT category_key,count(*),count(price),sum(price) FROM mart.v_order_items WHERE is_revenue GROUP BY category_key
         EXCEPT ALL SELECT b.category_key,count(*),count(i.price),sum(i.price)
         FROM core.fact_order_item i JOIN core.fact_order o USING(order_id)
         JOIN core.dim_order_status s USING(order_status)
         JOIN history.report_binding b ON b.release_id=chosen AND b.order_id=i.order_id AND b.order_item_id=i.order_item_id
         WHERE s.is_revenue GROUP BY b.category_key))
    THEN RAISE EXCEPTION 'Historical category mart fanout/money mismatch'; END IF;
END $$;
SELECT history.check_model();
