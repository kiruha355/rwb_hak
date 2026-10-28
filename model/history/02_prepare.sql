-- Bootstrap once. A rebuild never imports live events or invents an Olist start.
DO $$
DECLARE original text; chosen text; closed timestamp;
BEGIN
    IF NOT EXISTS (SELECT FROM history.initial_release) THEN
        SELECT coalesce(max(order_purchase_timestamp::timestamp)+interval '1 microsecond',
            timestamp '2016-09-01') INTO closed FROM raw.orders;
        original := history.create_release('original-v1','original',NULL,'{}',closed);
        INSERT INTO history.initial_release VALUES(true,original);
    END IF;
    chosen := nullif(current_setting('capibara.report_release',true),'');
    IF chosen IS NULL THEN SELECT release_id INTO STRICT chosen FROM history.initial_release; END IF;
    PERFORM history.assert_release(chosen); -- BEFORE any destructive model DDL
    PERFORM set_config('capibara.report_release',chosen,true);
END $$;
