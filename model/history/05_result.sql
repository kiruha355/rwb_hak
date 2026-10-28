DO $$
DECLARE t text; manifest jsonb := '{}'; rows_digest text; chosen text; prior jsonb;
BEGIN
    SELECT release_id INTO STRICT chosen FROM core.model_release;
    FOREACH t IN ARRAY ARRAY['q01_revenue_monthly','q02_sellers_top10','q03_average_order',
        'q04_buyers_repeat','q04_buyers_repeat_q1_window','q05_category_revenue',
        'q06_price_history','q07_delivery_by_state','q08_status_snapshot',
        'q09_payments_2018_by_state','q09_payment_methods','q10_review_delivery','q10_review_coverage'] LOOP
        EXECUTE format('SELECT history.digest(coalesce(jsonb_agg(row ORDER BY row::text COLLATE "C"),''[]''))
            FROM (SELECT to_jsonb(r) AS row FROM mart.%I r) s',t) INTO rows_digest;
        manifest := manifest || jsonb_build_object(t,rows_digest);
    END LOOP;
    SELECT result_manifest INTO prior FROM history.report_result WHERE release_id=chosen;
    IF FOUND THEN
        IF prior<>manifest THEN RAISE EXCEPTION 'Pinned Q1-Q10 result changed for release %',chosen; END IF;
    ELSE
        INSERT INTO history.report_result VALUES(chosen,manifest);
    END IF;
END $$;
