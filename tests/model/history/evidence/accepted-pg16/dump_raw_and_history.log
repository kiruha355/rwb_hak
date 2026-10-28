--
-- PostgreSQL database dump
--

\restrict ASwq91XjwhGkFfeedWghEDnaRSwM5An0989Ftpbg3G8BrYhbjqwR2txDhyfkD8l

-- Dumped from database version 16.15 (Homebrew)
-- Dumped by pg_dump version 16.15 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: history; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA history;


--
-- Name: raw; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA raw;


--
-- Name: append_event(text, text, text, text, text, timestamp without time zone, timestamp without time zone, text, text, jsonb); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.append_event(p_id text, p_product text, p_seller text, p_action text, p_category text, p_valid_from timestamp without time zone, p_policy_from timestamp without time zone, p_clock text, p_supersedes text, p_provenance jsonb) RETURNS text
    LANGUAGE plpgsql
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE payload text; old history.category_event; target history.category_event;
BEGIN
    -- Same cooperating-writer lock as model builds. No hidden retry on stale RR snapshots.
    IF NOT pg_try_advisory_xact_lock(1667330674,1) THEN
        RAISE EXCEPTION 'Another cooperating Capibara model command is active';
    END IF;
    payload := history.digest(jsonb_build_array(p_id,p_product,p_seller,p_action,p_category,
        to_char(p_valid_from,'YYYY-MM-DD HH24:MI:SS.US'),
        to_char(p_policy_from,'YYYY-MM-DD HH24:MI:SS.US'),p_clock,p_supersedes,p_provenance));
    SELECT * INTO old FROM history.category_event WHERE event_id=p_id;
    IF FOUND THEN
        IF old.payload_sha256 <> payload THEN RAISE EXCEPTION 'Conflicting event identity: %',p_id; END IF;
        RETURN p_id;
    END IF;
    IF p_supersedes IS NOT NULL THEN
        SELECT * INTO STRICT target FROM history.category_event WHERE event_id=p_supersedes;
        IF ROW(target.product_id,target.seller_id) IS DISTINCT FROM ROW(p_product,p_seller) THEN
            RAISE EXCEPTION 'Correction scope mismatch';
        END IF;
        -- Existing target only, unique incoming edge: no cycles or correction forks.
    END IF;
    INSERT INTO history.category_event(event_id,product_id,seller_id,action,category_key,
        business_valid_from,policy_apply_from,clock_contract,supersedes_event_id,provenance,payload_sha256)
    VALUES(p_id,p_product,p_seller,p_action,p_category,p_valid_from,p_policy_from,p_clock,
        p_supersedes,p_provenance,payload);
    RETURN p_id;
END $$;


--
-- Name: assert_release(text); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.assert_release(p_id text) RETURNS void
    LANGUAGE plpgsql STABLE
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE r history.report_release; actual text;
BEGIN
    PERFORM history.assert_source();
    SELECT * INTO STRICT r FROM history.report_release WHERE release_id=p_id;
    SELECT history.digest(coalesce(jsonb_agg(to_jsonb(s) ORDER BY source_table COLLATE "C",row_hash),'[]'))
        INTO actual FROM history.source_rows() s;
    IF actual<>r.source_digest THEN RAISE EXCEPTION 'Raw generation differs from pinned release %',p_id; END IF;
    SELECT history.digest(coalesce(jsonb_agg(to_jsonb(s)-'release_id' ORDER BY source_table COLLATE "C",row_hash),'[]'))
        INTO actual FROM history.release_source_row s WHERE release_id=p_id;
    IF actual<>r.source_digest THEN RAISE EXCEPTION 'Source manifest corruption'; END IF;
    SELECT history.digest(coalesce(jsonb_agg(to_jsonb(b)-'release_id' ORDER BY order_id COLLATE "C",order_item_id),'[]'))
        INTO actual FROM history.report_binding b WHERE release_id=p_id;
    IF actual<>r.binding_digest THEN RAISE EXCEPTION 'Binding manifest corruption'; END IF;
    SELECT history.digest(jsonb_agg(to_jsonb(c)-'release_id' ORDER BY category_key COLLATE "C"))
        INTO actual FROM history.release_category c WHERE release_id=p_id;
    IF actual IS DISTINCT FROM r.taxonomy_digest THEN RAISE EXCEPTION 'Taxonomy manifest corruption'; END IF;
    IF EXISTS (SELECT FROM unnest(r.event_ids) x WHERE NOT EXISTS
        (SELECT FROM history.category_event WHERE event_id=x))
    THEN RAISE EXCEPTION 'Missing pinned event'; END IF;
    IF EXISTS (SELECT FROM history.report_binding b LEFT JOIN raw.order_items i
        ON i.order_id=b.order_id AND i.order_item_id::integer=b.order_item_id
        WHERE b.release_id=p_id AND (i.order_id IS NULL
            OR ROW(i.product_id,i.seller_id,history.digest(to_jsonb(i)-'_loaded_at'-'_source_file'))
               IS DISTINCT FROM ROW(b.product_id,b.seller_id,b.source_item_sha256)))
       OR (SELECT count(*) FROM history.report_binding WHERE release_id=p_id)<>(SELECT count(*) FROM raw.order_items)
    THEN RAISE EXCEPTION 'Item binding coverage/payload mismatch'; END IF;
    IF EXISTS (SELECT FROM history.report_binding b
        LEFT JOIN history.baseline_product bp ON bp.baseline_id=b.baseline_id AND bp.product_id=b.product_id
        LEFT JOIN history.category_event e ON e.event_id=b.event_id
        LEFT JOIN history.release_category c ON c.release_id=b.release_id AND c.category_key=b.category_key
        WHERE b.release_id=p_id AND (c.category_key IS NULL
          OR (b.baseline_id IS NOT NULL AND ROW(b.version_id,b.category_key,b.attribution_basis)
              IS DISTINCT FROM ROW(bp.version_id,bp.category_key,'snapshot_at_bootstrap'::text))
          OR (b.event_id IS NOT NULL AND (
              NOT b.event_id=ANY(r.event_ids) OR e.action<>'set' OR e.product_id<>b.product_id
              OR (e.seller_id IS NOT NULL AND e.seller_id<>b.seller_id)
              OR ROW(b.version_id,b.category_key,b.attribution_basis) IS DISTINCT FROM
                 ROW('e:'||e.payload_sha256,e.category_key,CASE WHEN e.business_valid_from IS NOT NULL
                     THEN 'asserted_valid_time' ELSE 'observed_since_policy' END)))))
    THEN RAISE EXCEPTION 'Binding source/version mismatch'; END IF;
END $$;


--
-- Name: assert_source(); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.assert_source() RETURNS void
    LANGUAGE plpgsql STABLE
    SET search_path TO 'pg_catalog'
    AS $$
BEGIN
    IF EXISTS (SELECT FROM history.baseline_snapshot s LEFT JOIN (
        SELECT baseline_id,history.digest(jsonb_agg(jsonb_build_array(product_id,
            CASE WHEN category_key='unknown' THEN NULL ELSE substr(category_key,4) END)
            ORDER BY product_id COLLATE "C")) AS content_id
        FROM history.baseline_product GROUP BY baseline_id
    ) b USING(baseline_id) WHERE s.baseline_id<>coalesce(b.content_id,history.digest('[]'::jsonb)))
       OR EXISTS (SELECT FROM history.baseline_product WHERE version_id<>'b:'||history.digest(jsonb_build_array(baseline_id,product_id)))
    THEN RAISE EXCEPTION 'Baseline source digest mismatch'; END IF;
    IF EXISTS (SELECT FROM history.category_event e WHERE e.payload_sha256<>history.digest(jsonb_build_array(
        event_id,product_id,seller_id,action,category_key,
        to_char(business_valid_from,'YYYY-MM-DD HH24:MI:SS.US'),
        to_char(policy_apply_from,'YYYY-MM-DD HH24:MI:SS.US'),clock_contract,supersedes_event_id,provenance)))
    THEN RAISE EXCEPTION 'Event source digest mismatch'; END IF;
    IF EXISTS (SELECT FROM history.category_event c JOIN history.category_event old ON old.event_id=c.supersedes_event_id
        WHERE ROW(c.product_id,c.seller_id) IS DISTINCT FROM ROW(old.product_id,old.seller_id))
    THEN RAISE EXCEPTION 'Correction source scope mismatch'; END IF;
    IF EXISTS (WITH RECURSIVE chain AS (
        SELECT event_id,supersedes_event_id,ARRAY[event_id] AS path,false AS cycle
        FROM history.category_event
        UNION ALL
        SELECT e.event_id,e.supersedes_event_id,c.path||e.event_id,e.event_id=ANY(c.path)
        FROM chain c JOIN history.category_event e ON e.event_id=c.supersedes_event_id WHERE NOT c.cycle
    ) SELECT FROM chain WHERE cycle)
    THEN RAISE EXCEPTION 'Correction source cycle'; END IF;
END $$;


--
-- Name: capture_baseline(); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.capture_baseline() RETURNS text
    LANGUAGE plpgsql
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE ident text;
BEGIN
    IF NOT pg_try_advisory_xact_lock(1667330674,1) THEN
        RAISE EXCEPTION 'Another cooperating Capibara model command is active';
    END IF;
    SELECT history.digest(coalesce(jsonb_agg(jsonb_build_array(product_id,product_category_name)
        ORDER BY product_id COLLATE "C"),'[]')) INTO ident FROM raw.products;
    IF NOT EXISTS (SELECT FROM history.baseline_snapshot WHERE baseline_id=ident) THEN
        INSERT INTO history.baseline_product
        SELECT ident, product_id, coalesce('pt:'||product_category_name,'unknown'),
            'b:'||history.digest(jsonb_build_array(ident,product_id)) FROM raw.products;
        INSERT INTO history.baseline_snapshot(baseline_id) VALUES(ident);
    END IF;
    RETURN ident;
END $$;


--
-- Name: check_model(); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.check_model() RETURNS void
    LANGUAGE plpgsql
    SET search_path TO 'pg_catalog'
    AS $$
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


--
-- Name: create_release(text, text, text, text[], timestamp without time zone); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.create_release(p_id text, p_kind text, p_parent text, p_events text[], p_closed_before timestamp without time zone) RETURNS text
    LANGUAGE plpgsql
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE baseline text; events text[]; src_digest text; bind_digest text; tax_digest text;
    prior history.report_release; parent history.report_release;
BEGIN
    IF NOT pg_try_advisory_xact_lock(1667330674,1) THEN
        RAISE EXCEPTION 'Another cooperating Capibara model command is active';
    END IF;
    PERFORM history.assert_source();
    SELECT coalesce(array_agg(DISTINCT e ORDER BY e),'{}') INTO events FROM unnest(p_events) e;
    IF p_events IS NULL OR array_position(p_events,NULL) IS NOT NULL
       OR cardinality(events)<>cardinality(p_events) THEN RAISE EXCEPTION 'Invalid event set'; END IF;
    IF EXISTS (SELECT FROM unnest(events) x LEFT JOIN history.category_event e ON e.event_id=x WHERE e.event_id IS NULL)
    THEN RAISE EXCEPTION 'Missing event in pinned set'; END IF;
    IF EXISTS (SELECT FROM history.category_event WHERE event_id=ANY(events)
        AND supersedes_event_id IS NOT NULL AND NOT supersedes_event_id=ANY(events))
    THEN RAISE EXCEPTION 'Incomplete correction chain'; END IF;
    IF EXISTS (SELECT FROM history.category_event e WHERE e.event_id=ANY(events)
        AND coalesce(e.business_valid_from,e.policy_apply_from) IS NOT NULL
        AND NOT EXISTS (SELECT FROM history.category_event c WHERE c.event_id=ANY(events) AND c.supersedes_event_id=e.event_id)
        GROUP BY product_id,seller_id,coalesce(business_valid_from,policy_apply_from) HAVING count(*)>1)
    THEN RAISE EXCEPTION 'Ambiguous category boundary'; END IF;
    SELECT history.digest(coalesce(jsonb_agg(to_jsonb(s) ORDER BY source_table COLLATE "C",row_hash),'[]'))
        INTO src_digest FROM history.source_rows() s;
    SELECT * INTO prior FROM history.report_release WHERE release_id=p_id;
    IF FOUND THEN
        IF ROW(prior.release_kind,prior.parent_release_id,prior.event_ids,prior.closed_before,prior.source_digest)
           IS DISTINCT FROM ROW(p_kind,p_parent,events,p_closed_before,src_digest)
        THEN RAISE EXCEPTION 'Conflicting release identity: %',p_id; END IF;
        RETURN p_id;
    END IF;
    IF p_kind NOT IN ('original','extension','restatement') OR p_kind IS NULL
       OR (p_kind='original') IS DISTINCT FROM (p_parent IS NULL)
    THEN RAISE EXCEPTION 'Invalid release kind/parent'; END IF;
    IF p_parent IS NOT NULL THEN
        SELECT * INTO STRICT parent FROM history.report_release WHERE release_id=p_parent;
    END IF;
    IF p_kind='extension' THEN
        IF p_closed_before < parent.closed_before OR NOT parent.event_ids <@ events THEN
            RAISE EXCEPTION 'Extension cannot retract boundary or event knowledge';
        END IF;
        IF EXISTS (SELECT FROM history.release_source_row old LEFT JOIN history.source_rows() now
            ON now.source_table=old.source_table AND now.row_hash=old.row_hash
            WHERE old.release_id=p_parent AND coalesce(now.occurrences,0)<old.occurrences)
        THEN RAISE EXCEPTION 'Extension changed or removed parent source rows; use restatement'; END IF;
        IF EXISTS (
            SELECT FROM (
                SELECT 'orders' AS source_table,o.order_id,history.digest(to_jsonb(o)-'_loaded_at'-'_source_file') AS row_hash FROM raw.orders o
                UNION ALL SELECT 'order_items',i.order_id,history.digest(to_jsonb(i)-'_loaded_at'-'_source_file') FROM raw.order_items i
                UNION ALL SELECT 'order_payments',p.order_id,history.digest(to_jsonb(p)-'_loaded_at'-'_source_file') FROM raw.order_payments p
                UNION ALL SELECT 'order_reviews',r.order_id,history.digest(to_jsonb(r)-'_loaded_at'-'_source_file') FROM raw.order_reviews r
            ) added JOIN raw.orders o USING(order_id)
            WHERE NOT EXISTS (SELECT FROM history.release_source_row old WHERE old.release_id=p_parent
                AND old.source_table=added.source_table AND old.row_hash=added.row_hash)
            AND (o.order_purchase_timestamp IS NULL OR o.order_purchase_timestamp::timestamp < parent.closed_before))
        THEN RAISE EXCEPTION 'Late item/order/payment/review in closed period requires restatement'; END IF;
    END IF;
    baseline := history.capture_baseline();
    INSERT INTO history.release_source_row SELECT p_id,s.* FROM history.source_rows() s;
    IF p_kind='extension' THEN
        INSERT INTO history.report_binding SELECT p_id,order_id,order_item_id,product_id,seller_id,
            source_item_sha256,version_id,category_key,attribution_basis,baseline_id,event_id
            FROM history.report_binding WHERE release_id=p_parent;
    END IF;
    INSERT INTO history.report_binding
    SELECT p_id,i.order_id,i.order_item_id::integer,i.product_id,i.seller_id,
        history.digest(to_jsonb(i)-'_loaded_at'-'_source_file'),
        v.version_id,v.category_key,v.attribution_basis,v.baseline_id,v.event_id
    FROM raw.order_items i JOIN raw.orders o USING(order_id)
    CROSS JOIN LATERAL history.resolve_category(baseline,events,i.product_id,i.seller_id,
        o.order_purchase_timestamp::timestamp) v
    WHERE NOT EXISTS (SELECT FROM history.report_binding b WHERE b.release_id=p_id
        AND b.order_id=i.order_id AND b.order_item_id=i.order_item_id::integer);
    IF (SELECT count(*) FROM history.report_binding WHERE release_id=p_id) <> (SELECT count(*) FROM raw.order_items)
    THEN RAISE EXCEPTION 'Release population mismatch'; END IF;
    -- Pin labels as well as category identities. New event categories need no fake translation.
    INSERT INTO history.release_category
    SELECT p_id,'unknown',NULL,NULL,true,false,false
    UNION ALL
    SELECT p_id,'pt:'||d.name,d.name,t.product_category_name_english,false,
        t.product_category_name_english IS NOT NULL,t.product_category_name IS NOT NULL
    FROM (
        SELECT product_category_name AS name FROM raw.products WHERE product_category_name IS NOT NULL
        UNION SELECT product_category_name FROM raw.product_category_translation
        UNION SELECT substr(category_key,4) FROM history.category_event WHERE event_id=ANY(events) AND category_key<>'unknown'
        UNION SELECT substr(category_key,4) FROM history.report_binding WHERE release_id=p_id AND category_key<>'unknown'
    ) d LEFT JOIN raw.product_category_translation t ON t.product_category_name=d.name;
    IF p_kind='extension' AND EXISTS (
        SELECT FROM history.release_category old LEFT JOIN history.release_category now
            ON now.release_id=p_id AND now.category_key=old.category_key
        WHERE old.release_id=p_parent AND (to_jsonb(old)-'release_id') IS DISTINCT FROM (to_jsonb(now)-'release_id'))
    THEN RAISE EXCEPTION 'Extension changed parent taxonomy; use restatement'; END IF;
    SELECT history.digest(coalesce(jsonb_agg(to_jsonb(b)-'release_id' ORDER BY order_id COLLATE "C",order_item_id),'[]'))
        INTO bind_digest FROM history.report_binding b WHERE release_id=p_id;
    SELECT history.digest(jsonb_agg(to_jsonb(c)-'release_id' ORDER BY category_key COLLATE "C"))
        INTO tax_digest FROM history.release_category c WHERE release_id=p_id;
    INSERT INTO history.report_release(release_id,parent_release_id,release_kind,baseline_id,event_ids,
        closed_before,source_digest,binding_digest,taxonomy_digest,policy_version)
    VALUES(p_id,p_parent,p_kind,baseline,events,p_closed_before,src_digest,bind_digest,tax_digest,'category_binding_v1');
    RETURN p_id;
END $$;


--
-- Name: digest(jsonb); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.digest(value jsonb) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    SET search_path TO 'pg_catalog'
    AS $$ SELECT encode(sha256(convert_to(value::text, 'UTF8')), 'hex') $$;


--
-- Name: immutable_guard(); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.immutable_guard() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path TO 'pg_catalog'
    AS $$
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'history source is immutable: %.% %', TG_TABLE_SCHEMA,TG_TABLE_NAME,TG_OP;
    END IF;
    IF TG_TABLE_NAME='baseline_product' THEN
        IF EXISTS (SELECT FROM history.baseline_snapshot WHERE baseline_id=NEW.baseline_id) THEN
            RAISE EXCEPTION 'baseline is sealed';
        END IF;
    ELSE
        IF EXISTS (SELECT FROM history.report_release WHERE release_id=NEW.release_id) THEN
            RAISE EXCEPTION 'release is sealed';
        END IF;
    END IF;
    RETURN NEW;
END $$;


--
-- Name: resolve_category(text, text[], text, text, timestamp without time zone); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.resolve_category(p_baseline text, p_events text[], p_product text, p_seller text, p_purchase timestamp without time zone) RETURNS TABLE(version_id text, category_key text, attribution_basis text, baseline_id text, event_id text)
    LANGUAGE plpgsql STABLE
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE chosen history.category_event; scope_seller text;
BEGIN
    FOREACH scope_seller IN ARRAY ARRAY[p_seller,NULL::text] LOOP
        SELECT e.* INTO chosen FROM history.category_event e
        WHERE e.event_id=ANY(p_events) AND e.product_id=p_product
          AND e.seller_id IS NOT DISTINCT FROM scope_seller
          AND coalesce(e.business_valid_from,e.policy_apply_from) <= p_purchase
          AND NOT EXISTS (SELECT FROM history.category_event c
              WHERE c.event_id=ANY(p_events) AND c.supersedes_event_id=e.event_id)
        ORDER BY coalesce(e.business_valid_from,e.policy_apply_from) DESC LIMIT 1;
        IF FOUND AND chosen.action='set' THEN
            RETURN QUERY SELECT 'e:'||chosen.payload_sha256, chosen.category_key,
                CASE WHEN chosen.business_valid_from IS NOT NULL THEN 'asserted_valid_time'
                     ELSE 'observed_since_policy' END, NULL::text, chosen.event_id;
            RETURN;
        END IF;
    END LOOP;
    RETURN QUERY SELECT b.version_id,b.category_key,'snapshot_at_bootstrap'::text,b.baseline_id,NULL::text
        FROM history.baseline_product b WHERE b.baseline_id=p_baseline AND b.product_id=p_product;
    IF NOT FOUND THEN RAISE EXCEPTION 'No baseline for product %',p_product; END IF;
END $$;


--
-- Name: source_rows(); Type: FUNCTION; Schema: history; Owner: -
--

CREATE FUNCTION history.source_rows() RETURNS TABLE(source_table text, row_hash text, occurrences bigint)
    LANGUAGE plpgsql STABLE
    SET search_path TO 'pg_catalog'
    AS $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['orders','order_items','order_payments','order_reviews',
        'products','sellers','customers','product_category_translation'] LOOP
        RETURN QUERY EXECUTE format(
            'SELECT %L, history.digest(to_jsonb(r)-''_loaded_at''-''_source_file''), count(*)
             FROM raw.%I r GROUP BY 2', t, t);
    END LOOP;
END $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: baseline_product; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.baseline_product (
    baseline_id text NOT NULL,
    product_id text NOT NULL,
    category_key text NOT NULL,
    version_id text NOT NULL,
    CONSTRAINT baseline_product_category_key_check CHECK (((category_key = 'unknown'::text) OR (category_key ~~ 'pt:%'::text)))
);


--
-- Name: baseline_snapshot; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.baseline_snapshot (
    baseline_id text NOT NULL,
    captured_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    business_valid_from timestamp without time zone,
    basis text DEFAULT 'snapshot_at_bootstrap'::text NOT NULL,
    CONSTRAINT baseline_snapshot_basis_check CHECK ((basis = 'snapshot_at_bootstrap'::text)),
    CONSTRAINT baseline_snapshot_business_valid_from_check CHECK ((business_valid_from IS NULL))
);


--
-- Name: category_event; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.category_event (
    event_id text NOT NULL,
    product_id text NOT NULL,
    seller_id text,
    action text NOT NULL,
    category_key text,
    business_valid_from timestamp without time zone,
    policy_apply_from timestamp without time zone,
    clock_contract text,
    supersedes_event_id text,
    provenance jsonb NOT NULL,
    payload_sha256 text NOT NULL,
    recorded_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    CONSTRAINT category_event_action_check CHECK ((action = ANY (ARRAY['set'::text, 'unset_override'::text]))),
    CONSTRAINT category_event_category_key_check CHECK (((category_key = 'unknown'::text) OR (category_key ~~ 'pt:%'::text))),
    CONSTRAINT category_event_check CHECK ((((action = 'set'::text) AND (category_key IS NOT NULL)) OR ((action = 'unset_override'::text) AND (seller_id IS NOT NULL) AND (category_key IS NULL)))),
    CONSTRAINT category_event_check1 CHECK (((business_valid_from IS NULL) OR (policy_apply_from IS NULL))),
    CONSTRAINT category_event_check2 CHECK (
CASE
    WHEN (COALESCE(business_valid_from, policy_apply_from) IS NOT NULL) THEN (NOT (clock_contract IS DISTINCT FROM 'source_naive_purchase_v1'::text))
    ELSE (clock_contract IS NULL)
END),
    CONSTRAINT category_event_check3 CHECK ((isfinite(business_valid_from) AND isfinite(policy_apply_from))),
    CONSTRAINT category_event_event_id_check CHECK ((event_id <> ''::text)),
    CONSTRAINT category_event_product_id_check CHECK ((product_id <> ''::text)),
    CONSTRAINT category_event_provenance_check CHECK (((jsonb_typeof(provenance) = 'object'::text) AND (provenance <> '{}'::jsonb))),
    CONSTRAINT category_event_seller_id_check CHECK ((seller_id <> ''::text))
);


--
-- Name: initial_release; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.initial_release (
    singleton boolean DEFAULT true NOT NULL,
    release_id text NOT NULL,
    CONSTRAINT initial_release_singleton_check CHECK (singleton)
);


--
-- Name: release_category; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.release_category (
    release_id text NOT NULL,
    category_key text NOT NULL,
    name_pt text,
    name_en text,
    is_unknown boolean NOT NULL,
    is_translated boolean NOT NULL,
    has_translation_row boolean NOT NULL,
    CONSTRAINT release_category_check CHECK (((is_unknown AND (category_key = 'unknown'::text) AND (name_pt IS NULL) AND (name_en IS NULL) AND (NOT is_translated) AND (NOT has_translation_row)) OR ((NOT is_unknown) AND (name_pt IS NOT NULL) AND (category_key = ('pt:'::text || name_pt)) AND (is_translated = (name_en IS NOT NULL)) AND (has_translation_row OR (name_en IS NULL)))))
);


--
-- Name: release_source_row; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.release_source_row (
    release_id text NOT NULL,
    source_table text NOT NULL,
    row_hash text NOT NULL,
    occurrences bigint NOT NULL,
    CONSTRAINT release_source_row_occurrences_check CHECK ((occurrences > 0))
);


--
-- Name: report_binding; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.report_binding (
    release_id text NOT NULL,
    order_id text NOT NULL,
    order_item_id integer NOT NULL,
    product_id text NOT NULL,
    seller_id text NOT NULL,
    source_item_sha256 text NOT NULL,
    version_id text NOT NULL,
    category_key text NOT NULL,
    attribution_basis text NOT NULL,
    baseline_id text,
    event_id text,
    CONSTRAINT report_binding_attribution_basis_check CHECK ((attribution_basis = ANY (ARRAY['snapshot_at_bootstrap'::text, 'asserted_valid_time'::text, 'observed_since_policy'::text]))),
    CONSTRAINT report_binding_check CHECK (((baseline_id IS NULL) <> (event_id IS NULL)))
);


--
-- Name: report_release; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.report_release (
    release_id text NOT NULL,
    parent_release_id text,
    release_kind text NOT NULL,
    baseline_id text NOT NULL,
    event_ids text[] NOT NULL,
    closed_before timestamp without time zone NOT NULL,
    source_digest text NOT NULL,
    binding_digest text NOT NULL,
    taxonomy_digest text NOT NULL,
    policy_version text NOT NULL,
    recorded_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    CONSTRAINT report_release_check CHECK (((release_kind = 'original'::text) = (parent_release_id IS NULL))),
    CONSTRAINT report_release_closed_before_check CHECK (isfinite(closed_before)),
    CONSTRAINT report_release_policy_version_check CHECK ((policy_version = 'category_binding_v1'::text)),
    CONSTRAINT report_release_release_id_check CHECK ((release_id <> ''::text)),
    CONSTRAINT report_release_release_kind_check CHECK ((release_kind = ANY (ARRAY['original'::text, 'extension'::text, 'restatement'::text])))
);


--
-- Name: report_result; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.report_result (
    release_id text NOT NULL,
    result_manifest jsonb NOT NULL
);


--
-- Name: schema_version; Type: TABLE; Schema: history; Owner: -
--

CREATE TABLE history.schema_version (
    singleton boolean DEFAULT true NOT NULL,
    version integer NOT NULL,
    CONSTRAINT schema_version_singleton_check CHECK (singleton),
    CONSTRAINT schema_version_version_check CHECK ((version = 1))
);


--
-- Name: customers; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.customers (
    customer_id text,
    customer_unique_id text,
    customer_zip_code_prefix text,
    customer_city text,
    customer_state text,
    _source_file text,
    _loaded_at timestamp with time zone DEFAULT now()
);


--
-- Name: order_items; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.order_items (
    order_id text,
    order_item_id text,
    product_id text,
    seller_id text,
    shipping_limit_date text,
    price text,
    freight_value text,
    _source_file text,
    _loaded_at timestamp with time zone DEFAULT now()
);


--
-- Name: order_payments; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.order_payments (
    order_id text,
    payment_sequential text,
    payment_type text,
    payment_installments text,
    payment_value text,
    _source_file text,
    _loaded_at timestamp with time zone DEFAULT now()
);


--
-- Name: order_reviews; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.order_reviews (
    review_id text,
    order_id text,
    review_score text,
    review_comment_title text,
    review_comment_message text,
    review_creation_date text,
    review_answer_timestamp text,
    _source_file text,
    _loaded_at timestamp with time zone DEFAULT now()
);


--
-- Name: orders; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.orders (
    order_id text,
    customer_id text,
    order_status text,
    order_purchase_timestamp text,
    order_approved_at text,
    order_delivered_carrier_date text,
    order_delivered_customer_date text,
    order_estimated_delivery_date text,
    _source_file text,
    _loaded_at timestamp with time zone DEFAULT now()
);


--
-- Name: product_category_translation; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.product_category_translation (
    product_category_name text,
    product_category_name_english text,
    _source_file text,
    _loaded_at timestamp with time zone DEFAULT now()
);


--
-- Name: products; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.products (
    product_id text,
    product_category_name text,
    product_name_lenght text,
    product_description_lenght text,
    product_photos_qty text,
    product_weight_g text,
    product_length_cm text,
    product_height_cm text,
    product_width_cm text,
    _source_file text,
    _loaded_at timestamp with time zone DEFAULT now()
);


--
-- Name: sellers; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.sellers (
    seller_id text,
    seller_zip_code_prefix text,
    seller_city text,
    seller_state text,
    _source_file text,
    _loaded_at timestamp with time zone DEFAULT now()
);


--
-- Data for Name: baseline_product; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.baseline_product (baseline_id, product_id, category_key, version_id) FROM stdin;
871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	P	pt:A	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2
\.


--
-- Data for Name: baseline_snapshot; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.baseline_snapshot (baseline_id, captured_at, business_valid_from, basis) FROM stdin;
871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	2026-10-28 17:05:32.733897+03	\N	snapshot_at_bootstrap
\.


--
-- Data for Name: category_event; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.category_event (event_id, product_id, seller_id, action, category_key, business_valid_from, policy_apply_from, clock_contract, supersedes_event_id, provenance, payload_sha256, recorded_at) FROM stdin;
E1	P	S1	set	pt:B	2018-01-10 00:00:00	\N	source_naive_purchase_v1	\N	{"source": "synthetic-test"}	b7cf6ce7175de1abe0637288d7152107f054b24a21d5e0e082cf22509558e6ff	2026-10-28 17:05:32.885214+03
E2	P	S1	set	pt:B	2018-01-04 00:00:00	\N	source_naive_purchase_v1	E1	{"source": "synthetic-test"}	f0deedac8ac9116df2504b6836523f8960f509f85764f97f16a1860929ff3951	2026-10-28 17:05:33.466746+03
E3	P	\N	set	pt:C	2018-01-21 00:00:00	\N	source_naive_purchase_v1	\N	{"source": "synthetic-test"}	f72d7c2b9994de5e3ccf736fdc08efd3979506a3937208ffe976344195d2bd04	2026-10-28 17:05:33.817755+03
E4	P	S1	unset_override	\N	2018-01-23 00:00:00	\N	source_naive_purchase_v1	\N	{"source": "synthetic-test"}	7486cb869ca0048e15917f4b70ac8de11d3e0e1720e9f282c34546e067242352	2026-10-28 17:05:33.826585+03
E5	P	S2	set	pt:D	\N	2018-01-25 00:00:00	source_naive_purchase_v1	\N	{"source": "synthetic-test"}	9ebfb307bde1458ede77e94bd445ce642f4849c8b36467d339419dbbd18ca117	2026-10-28 17:05:33.835252+03
E6	P	S2	set	unknown	2018-01-27 00:00:00	\N	source_naive_purchase_v1	\N	{"source": "synthetic-test"}	a11ee8062aea7e1c4a77d2dca79c2b2454aaf57da2aaffbb3075f27841d1750c	2026-10-28 17:05:33.84389+03
E7	P	\N	set	pt:A	2018-01-28 00:00:00	\N	source_naive_purchase_v1	\N	{"source": "synthetic-test"}	c1e04a9e50be479e071eb50e49f1ab8cd854eec3ef3d57b371dd9638180ff126	2026-10-28 17:05:33.852344+03
observation-only	P	S2	set	pt:Z	\N	\N	\N	\N	{"source": "synthetic-test"}	c6a3a1f5fa137af0178dfcb3300dec1fb737b6b8d5ac4e2735d76d890b6e0e75	2026-10-28 17:05:33.867379+03
ambiguous	P	\N	set	pt:B	2018-01-21 00:00:00	\N	source_naive_purchase_v1	\N	{"source": "synthetic-test"}	28041a83521a3f9c243d115df5441ff19b241734d4fa6d1fe7e958ba92cd1325	2026-10-28 17:05:33.883853+03
\.


--
-- Data for Name: initial_release; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.initial_release (singleton, release_id) FROM stdin;
t	original-v1
\.


--
-- Data for Name: release_category; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.release_category (release_id, category_key, name_pt, name_en, is_unknown, is_translated, has_translation_row) FROM stdin;
original-v1	unknown	\N	\N	t	f	f
original-v1	pt:A	A	alpha	f	t	t
original-v1	pt:B	B	beta	f	t	t
original-v1	pt:C	C	gamma	f	t	t
R1	unknown	\N	\N	t	f	f
R1	pt:A	A	alpha	f	t	t
R1	pt:B	B	beta	f	t	t
R1	pt:C	C	gamma	f	t	t
R1-restated	unknown	\N	\N	t	f	f
R1-restated	pt:A	A	alpha	f	t	t
R1-restated	pt:B	B	beta	f	t	t
R1-restated	pt:C	C	gamma	f	t	t
R-policy	unknown	\N	\N	t	f	f
R-policy	pt:A	A	alpha	f	t	t
R-policy	pt:B	B	beta	f	t	t
R-policy	pt:C	C	gamma	f	t	t
R-policy	pt:D	D	\N	f	f	f
\.


--
-- Data for Name: release_source_row; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.release_source_row (release_id, source_table, row_hash, occurrences) FROM stdin;
original-v1	orders	47cc25b68e1e6ccaee845481d657263ba9f038766559ca988db026bd802d46c7	1
original-v1	orders	1621e2e158a0be75f0ac984d2787b818123fb05fe9032b26de3761ae5158c709	1
original-v1	order_items	1512c5cf075c2ca123a541d9ed7134c188bba068d3ef4bf02f53ad21a3977b05	1
original-v1	order_items	86388635c71fb993a669e8ec645435b9c5846b0a15965f5f2917e19067d7dce4	1
original-v1	products	364dbfc10b0d824b56c095bbd6a5efaef07b510edecf478953e683a7cca3a82c	1
original-v1	sellers	f051bbc130dccad203252878683ecd773f1821531b418b73c9affb6eb0db19de	1
original-v1	sellers	cfe21f1a285c7106d88b0c30c6d85b6d5a801209cee9868bd7467066595054bc	1
original-v1	customers	b42800e6b9bf0c9b604ccf140142e7aeb0047ae8e947dbbfb36b48c38e9d8a23	1
original-v1	customers	56517e3373b0ab3e3fc348dd85e070890f1eae909ad407dd9d0b583ea43292b0	1
original-v1	product_category_translation	930e2a6fac1c6c22bdcd6c5ce93e0f43a9b4d5d5c5a7b4fa25c41b6a0f8111cc	1
original-v1	product_category_translation	06a99c1ef9164fab08cad524c8ced99a7db8f8f5d8eed89426e6763f78ce3056	1
original-v1	product_category_translation	4ee335aedffbdc89ae35539536d89ce2789972183b449dd554c4c21bd7f39627	1
R1	orders	47cc25b68e1e6ccaee845481d657263ba9f038766559ca988db026bd802d46c7	1
R1	orders	1621e2e158a0be75f0ac984d2787b818123fb05fe9032b26de3761ae5158c709	1
R1	orders	543d79a59d458a83b79adf4f6969cbc4d64a5c7895ccbc6d19fa2203267d5382	1
R1	orders	f1beff14f446863ddde525ed7a63e9282acc4e5c8ab616f3c241f792379605a1	1
R1	order_items	1512c5cf075c2ca123a541d9ed7134c188bba068d3ef4bf02f53ad21a3977b05	1
R1	order_items	06e3fac74b50570a738f001842b657de1fb4fd164e61885ae54c3ec10d8dca5c	1
R1	order_items	338027f1b6186cea5c6a0a062c6bffd592d73495ec2c9ec4e9e1bf586c28c789	1
R1	order_items	86388635c71fb993a669e8ec645435b9c5846b0a15965f5f2917e19067d7dce4	1
R1	products	364dbfc10b0d824b56c095bbd6a5efaef07b510edecf478953e683a7cca3a82c	1
R1	sellers	f051bbc130dccad203252878683ecd773f1821531b418b73c9affb6eb0db19de	1
R1	sellers	cfe21f1a285c7106d88b0c30c6d85b6d5a801209cee9868bd7467066595054bc	1
R1	customers	26c8baf5db0ef94d57c4dd7baebc55ecaf935e7f38ea10e4074d010261f628a5	1
R1	customers	b42800e6b9bf0c9b604ccf140142e7aeb0047ae8e947dbbfb36b48c38e9d8a23	1
R1	customers	56517e3373b0ab3e3fc348dd85e070890f1eae909ad407dd9d0b583ea43292b0	1
R1	customers	d11c38218c68b35fe3cd81f67ca96932a66fa8278d8d4bafec22e252b7dbaa81	1
R1	product_category_translation	930e2a6fac1c6c22bdcd6c5ce93e0f43a9b4d5d5c5a7b4fa25c41b6a0f8111cc	1
R1	product_category_translation	06a99c1ef9164fab08cad524c8ced99a7db8f8f5d8eed89426e6763f78ce3056	1
R1	product_category_translation	4ee335aedffbdc89ae35539536d89ce2789972183b449dd554c4c21bd7f39627	1
R1-restated	orders	47cc25b68e1e6ccaee845481d657263ba9f038766559ca988db026bd802d46c7	1
R1-restated	orders	1621e2e158a0be75f0ac984d2787b818123fb05fe9032b26de3761ae5158c709	1
R1-restated	orders	543d79a59d458a83b79adf4f6969cbc4d64a5c7895ccbc6d19fa2203267d5382	1
R1-restated	orders	f1beff14f446863ddde525ed7a63e9282acc4e5c8ab616f3c241f792379605a1	1
R1-restated	order_items	1512c5cf075c2ca123a541d9ed7134c188bba068d3ef4bf02f53ad21a3977b05	1
R1-restated	order_items	06e3fac74b50570a738f001842b657de1fb4fd164e61885ae54c3ec10d8dca5c	1
R1-restated	order_items	338027f1b6186cea5c6a0a062c6bffd592d73495ec2c9ec4e9e1bf586c28c789	1
R1-restated	order_items	86388635c71fb993a669e8ec645435b9c5846b0a15965f5f2917e19067d7dce4	1
R1-restated	products	364dbfc10b0d824b56c095bbd6a5efaef07b510edecf478953e683a7cca3a82c	1
R1-restated	sellers	f051bbc130dccad203252878683ecd773f1821531b418b73c9affb6eb0db19de	1
R1-restated	sellers	cfe21f1a285c7106d88b0c30c6d85b6d5a801209cee9868bd7467066595054bc	1
R1-restated	customers	26c8baf5db0ef94d57c4dd7baebc55ecaf935e7f38ea10e4074d010261f628a5	1
R1-restated	customers	b42800e6b9bf0c9b604ccf140142e7aeb0047ae8e947dbbfb36b48c38e9d8a23	1
R1-restated	customers	56517e3373b0ab3e3fc348dd85e070890f1eae909ad407dd9d0b583ea43292b0	1
R1-restated	customers	d11c38218c68b35fe3cd81f67ca96932a66fa8278d8d4bafec22e252b7dbaa81	1
R1-restated	product_category_translation	930e2a6fac1c6c22bdcd6c5ce93e0f43a9b4d5d5c5a7b4fa25c41b6a0f8111cc	1
R1-restated	product_category_translation	06a99c1ef9164fab08cad524c8ced99a7db8f8f5d8eed89426e6763f78ce3056	1
R1-restated	product_category_translation	4ee335aedffbdc89ae35539536d89ce2789972183b449dd554c4c21bd7f39627	1
R-policy	orders	47cc25b68e1e6ccaee845481d657263ba9f038766559ca988db026bd802d46c7	1
R-policy	orders	1621e2e158a0be75f0ac984d2787b818123fb05fe9032b26de3761ae5158c709	1
R-policy	orders	543d79a59d458a83b79adf4f6969cbc4d64a5c7895ccbc6d19fa2203267d5382	1
R-policy	orders	f1beff14f446863ddde525ed7a63e9282acc4e5c8ab616f3c241f792379605a1	1
R-policy	order_items	1512c5cf075c2ca123a541d9ed7134c188bba068d3ef4bf02f53ad21a3977b05	1
R-policy	order_items	06e3fac74b50570a738f001842b657de1fb4fd164e61885ae54c3ec10d8dca5c	1
R-policy	order_items	338027f1b6186cea5c6a0a062c6bffd592d73495ec2c9ec4e9e1bf586c28c789	1
R-policy	order_items	86388635c71fb993a669e8ec645435b9c5846b0a15965f5f2917e19067d7dce4	1
R-policy	products	364dbfc10b0d824b56c095bbd6a5efaef07b510edecf478953e683a7cca3a82c	1
R-policy	sellers	f051bbc130dccad203252878683ecd773f1821531b418b73c9affb6eb0db19de	1
R-policy	sellers	cfe21f1a285c7106d88b0c30c6d85b6d5a801209cee9868bd7467066595054bc	1
R-policy	customers	26c8baf5db0ef94d57c4dd7baebc55ecaf935e7f38ea10e4074d010261f628a5	1
R-policy	customers	b42800e6b9bf0c9b604ccf140142e7aeb0047ae8e947dbbfb36b48c38e9d8a23	1
R-policy	customers	56517e3373b0ab3e3fc348dd85e070890f1eae909ad407dd9d0b583ea43292b0	1
R-policy	customers	d11c38218c68b35fe3cd81f67ca96932a66fa8278d8d4bafec22e252b7dbaa81	1
R-policy	product_category_translation	930e2a6fac1c6c22bdcd6c5ce93e0f43a9b4d5d5c5a7b4fa25c41b6a0f8111cc	1
R-policy	product_category_translation	06a99c1ef9164fab08cad524c8ced99a7db8f8f5d8eed89426e6763f78ce3056	1
R-policy	product_category_translation	4ee335aedffbdc89ae35539536d89ce2789972183b449dd554c4c21bd7f39627	1
\.


--
-- Data for Name: report_binding; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.report_binding (release_id, order_id, order_item_id, product_id, seller_id, source_item_sha256, version_id, category_key, attribution_basis, baseline_id, event_id) FROM stdin;
original-v1	old1	1	P	S1	86388635c71fb993a669e8ec645435b9c5846b0a15965f5f2917e19067d7dce4	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
original-v1	old2	1	P	S2	1512c5cf075c2ca123a541d9ed7134c188bba068d3ef4bf02f53ad21a3977b05	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
R1	old1	1	P	S1	86388635c71fb993a669e8ec645435b9c5846b0a15965f5f2917e19067d7dce4	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
R1	old2	1	P	S2	1512c5cf075c2ca123a541d9ed7134c188bba068d3ef4bf02f53ad21a3977b05	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
R1	new1	1	P	S1	06e3fac74b50570a738f001842b657de1fb4fd164e61885ae54c3ec10d8dca5c	e:b7cf6ce7175de1abe0637288d7152107f054b24a21d5e0e082cf22509558e6ff	pt:B	asserted_valid_time	\N	E1
R1	new2	1	P	S2	338027f1b6186cea5c6a0a062c6bffd592d73495ec2c9ec4e9e1bf586c28c789	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
R1-restated	old1	1	P	S1	86388635c71fb993a669e8ec645435b9c5846b0a15965f5f2917e19067d7dce4	e:f0deedac8ac9116df2504b6836523f8960f509f85764f97f16a1860929ff3951	pt:B	asserted_valid_time	\N	E2
R1-restated	old2	1	P	S2	1512c5cf075c2ca123a541d9ed7134c188bba068d3ef4bf02f53ad21a3977b05	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
R1-restated	new1	1	P	S1	06e3fac74b50570a738f001842b657de1fb4fd164e61885ae54c3ec10d8dca5c	e:f0deedac8ac9116df2504b6836523f8960f509f85764f97f16a1860929ff3951	pt:B	asserted_valid_time	\N	E2
R1-restated	new2	1	P	S2	338027f1b6186cea5c6a0a062c6bffd592d73495ec2c9ec4e9e1bf586c28c789	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
R-policy	old1	1	P	S1	86388635c71fb993a669e8ec645435b9c5846b0a15965f5f2917e19067d7dce4	e:f0deedac8ac9116df2504b6836523f8960f509f85764f97f16a1860929ff3951	pt:B	asserted_valid_time	\N	E2
R-policy	old2	1	P	S2	1512c5cf075c2ca123a541d9ed7134c188bba068d3ef4bf02f53ad21a3977b05	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
R-policy	new1	1	P	S1	06e3fac74b50570a738f001842b657de1fb4fd164e61885ae54c3ec10d8dca5c	e:f0deedac8ac9116df2504b6836523f8960f509f85764f97f16a1860929ff3951	pt:B	asserted_valid_time	\N	E2
R-policy	new2	1	P	S2	338027f1b6186cea5c6a0a062c6bffd592d73495ec2c9ec4e9e1bf586c28c789	b:0d71d0da90a4a96fca77e6490dae2213f3b6ba0bbd6cad2e137d1aee37e115b2	pt:A	snapshot_at_bootstrap	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	\N
\.


--
-- Data for Name: report_release; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.report_release (release_id, parent_release_id, release_kind, baseline_id, event_ids, closed_before, source_digest, binding_digest, taxonomy_digest, policy_version, recorded_at) FROM stdin;
original-v1	\N	original	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	{}	2018-01-05 00:00:00.000001	bbe3fa9f5c9b079f49dbb0b5dba38778ec8472f2d8eb41cde6e3c998f0af300b	0ac90290e0e9da3e0b45f768a77fb2ca0877dd6102c2b5afb4ab60acd3098999	be056237aa4c7a83f0315e6b5ea8f6a2ee1be734cce5e42636bbfb17a4ee29cb	category_binding_v1	2026-10-28 17:05:32.735727+03
R1	original-v1	extension	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	{E1}	2018-01-13 00:00:00	0bb1bd6d8569aa990d82e168c48d1eb956e57ae4dc3720c3284fd1c58a50d399	bfb0d3df7002d960e2b9914f7cc8d462c1565f12250f5e285055c274d6ffb7d5	be056237aa4c7a83f0315e6b5ea8f6a2ee1be734cce5e42636bbfb17a4ee29cb	category_binding_v1	2026-10-28 17:05:33.090454+03
R1-restated	R1	restatement	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	{E1,E2}	2018-01-13 00:00:00	0bb1bd6d8569aa990d82e168c48d1eb956e57ae4dc3720c3284fd1c58a50d399	b88b48237cfa5a1df0a1589691a556b1ac9c58857c461b308652c6472ecc1cda	be056237aa4c7a83f0315e6b5ea8f6a2ee1be734cce5e42636bbfb17a4ee29cb	category_binding_v1	2026-10-28 17:05:33.626802+03
R-policy	R1	restatement	871d906fe05b84db87af5f637a25d27227d1492b10e7b686da77c43adb4bb90d	{E1,E2,E3,E4,E5,E6,E7}	2018-01-13 00:00:00	0bb1bd6d8569aa990d82e168c48d1eb956e57ae4dc3720c3284fd1c58a50d399	b88b48237cfa5a1df0a1589691a556b1ac9c58857c461b308652c6472ecc1cda	22df5087fb85e186a4ab4af36097d377ad69b09897adf59adc62fbd3997cfbae	category_binding_v1	2026-10-28 17:05:33.926276+03
\.


--
-- Data for Name: report_result; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.report_result (release_id, result_manifest) FROM stdin;
original-v1	{"q02_sellers_top10": "03ec54c0ce17a3e60ab245784975d91af6af95ffe911c30c7e14470cdc032bfc", "q03_average_order": "39c17caa6eda70ac187635f0eb727ee2c2484a11c0a51eccf8e4b2c82999f5b2", "q04_buyers_repeat": "9a24bb3450f11b375fb2da76717c059d4a9e530404a20976a754bd1b6cd907af", "q06_price_history": "cd746e85f7c88bc3c1c345380da197abdefa5d93fc0461c4de8fdcdf59dbe929", "q01_revenue_monthly": "5184515faab93bd36bd5c51a807d8cc4cdff4a089dd0b308d5b85821c07365da", "q08_status_snapshot": "dc1b03af1c957e1fe2d1779c415732ba43ff3b6e515c7cc5efc5f3871fa5a926", "q09_payment_methods": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", "q10_review_coverage": "efb2c4d306ef2fb5dab3e03d4037b3059bf44adad51464d34b6aa180d46a1b9c", "q10_review_delivery": "4892c68c7f9005216c061b6d6246c81239268f86fa39ab9079513448afb5693d", "q05_category_revenue": "39b6b90a7e3689b9c2fd7c463c5a0ccbe668f7d1cb6bea55b5b7e1afc421f8b1", "q07_delivery_by_state": "1c665dfdf03d6938191470d0e6160b010b5f4fa1817e8a44bd2381398ac7e2b6", "q09_payments_2018_by_state": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", "q04_buyers_repeat_q1_window": "24cdf06df5454adf5ab396f89551eaf6b1ac054d1d06fb6f3b5ad2cbdcc3d32b"}
R1	{"q02_sellers_top10": "426b5d267aecce90b7ba1af0a1554c27d789e409eda133fd241d471ebe8f0639", "q03_average_order": "a1b53a73e062fb698c5356b11b94f04db168be98bb41fad84ae3b59842c2bc0d", "q04_buyers_repeat": "a7a129e9e74e964809457770a8d2cde8fd2cc73aa2f79620f4672581e7c72b16", "q06_price_history": "a9160dae8c65ed4b585244a6f5c72c1645e50f0769c26b7ba7196f1ee78f7424", "q01_revenue_monthly": "9c272891d8a3b95f2a26b93ac5af3b9b95e643d2572bb2112852f7ba1325ac42", "q08_status_snapshot": "9033af7c122fe3f2db99ab3671b91f2f608e59ce3f8c2fb397041e7985389f2d", "q09_payment_methods": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", "q10_review_coverage": "67a14ccd64f07e4075dab26b1b4368eb64dd59b3ac017ec96478c5d3defa18bc", "q10_review_delivery": "4892c68c7f9005216c061b6d6246c81239268f86fa39ab9079513448afb5693d", "q05_category_revenue": "ca6ba66fc49ddc5b8e13fbb3977334fa1cf7cc801ef8574683e8c10a6508d817", "q07_delivery_by_state": "da109e1d0ca1cf763d282dcc3695e5fe0ee6f0ffa9698db237043b676d6b629c", "q09_payments_2018_by_state": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", "q04_buyers_repeat_q1_window": "c45265e8ce3b8e260e70fb7a1a3b3c81da19356dddf1d74193911fdf070c7337"}
R1-restated	{"q02_sellers_top10": "426b5d267aecce90b7ba1af0a1554c27d789e409eda133fd241d471ebe8f0639", "q03_average_order": "a1b53a73e062fb698c5356b11b94f04db168be98bb41fad84ae3b59842c2bc0d", "q04_buyers_repeat": "a7a129e9e74e964809457770a8d2cde8fd2cc73aa2f79620f4672581e7c72b16", "q06_price_history": "a9160dae8c65ed4b585244a6f5c72c1645e50f0769c26b7ba7196f1ee78f7424", "q01_revenue_monthly": "9c272891d8a3b95f2a26b93ac5af3b9b95e643d2572bb2112852f7ba1325ac42", "q08_status_snapshot": "9033af7c122fe3f2db99ab3671b91f2f608e59ce3f8c2fb397041e7985389f2d", "q09_payment_methods": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", "q10_review_coverage": "67a14ccd64f07e4075dab26b1b4368eb64dd59b3ac017ec96478c5d3defa18bc", "q10_review_delivery": "4892c68c7f9005216c061b6d6246c81239268f86fa39ab9079513448afb5693d", "q05_category_revenue": "ec5c4e64b6147a326547be2f09fe4b068299470041be38155ae9a4003d53190c", "q07_delivery_by_state": "da109e1d0ca1cf763d282dcc3695e5fe0ee6f0ffa9698db237043b676d6b629c", "q09_payments_2018_by_state": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", "q04_buyers_repeat_q1_window": "c45265e8ce3b8e260e70fb7a1a3b3c81da19356dddf1d74193911fdf070c7337"}
R-policy	{"q02_sellers_top10": "426b5d267aecce90b7ba1af0a1554c27d789e409eda133fd241d471ebe8f0639", "q03_average_order": "a1b53a73e062fb698c5356b11b94f04db168be98bb41fad84ae3b59842c2bc0d", "q04_buyers_repeat": "a7a129e9e74e964809457770a8d2cde8fd2cc73aa2f79620f4672581e7c72b16", "q06_price_history": "a9160dae8c65ed4b585244a6f5c72c1645e50f0769c26b7ba7196f1ee78f7424", "q01_revenue_monthly": "9c272891d8a3b95f2a26b93ac5af3b9b95e643d2572bb2112852f7ba1325ac42", "q08_status_snapshot": "9033af7c122fe3f2db99ab3671b91f2f608e59ce3f8c2fb397041e7985389f2d", "q09_payment_methods": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", "q10_review_coverage": "67a14ccd64f07e4075dab26b1b4368eb64dd59b3ac017ec96478c5d3defa18bc", "q10_review_delivery": "4892c68c7f9005216c061b6d6246c81239268f86fa39ab9079513448afb5693d", "q05_category_revenue": "65bbffcba77b579409b51dd26a47ce7d1198c75b138352a2a044f4898bd8795e", "q07_delivery_by_state": "da109e1d0ca1cf763d282dcc3695e5fe0ee6f0ffa9698db237043b676d6b629c", "q09_payments_2018_by_state": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945", "q04_buyers_repeat_q1_window": "c45265e8ce3b8e260e70fb7a1a3b3c81da19356dddf1d74193911fdf070c7337"}
\.


--
-- Data for Name: schema_version; Type: TABLE DATA; Schema: history; Owner: -
--

COPY history.schema_version (singleton, version) FROM stdin;
t	1
\.


--
-- Data for Name: customers; Type: TABLE DATA; Schema: raw; Owner: -
--

COPY raw.customers (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state, _source_file, _loaded_at) FROM stdin;
c-old1	buyer	01000	city-old1	SP	\N	2026-10-28 17:05:32.676684+03
c-old2	buyer	20000	city-old2	RJ	\N	2026-10-28 17:05:32.676684+03
c-new1	buyer	30000	city-new1	MG	\N	2026-10-28 17:05:33.070305+03
c-new2	buyer	30000	city-new2	MG	\N	2026-10-28 17:05:33.070305+03
\.


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: raw; Owner: -
--

COPY raw.order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value, _source_file, _loaded_at) FROM stdin;
old1	1	P	S1	\N	100	0	\N	2026-10-28 17:05:32.676684+03
old2	1	P	S2	\N	200	0	\N	2026-10-28 17:05:32.676684+03
new1	1	P	S1	\N	30	0	\N	2026-10-28 17:05:33.070305+03
new2	1	P	S2	\N	40	0	\N	2026-10-28 17:05:33.070305+03
\.


--
-- Data for Name: order_payments; Type: TABLE DATA; Schema: raw; Owner: -
--

COPY raw.order_payments (order_id, payment_sequential, payment_type, payment_installments, payment_value, _source_file, _loaded_at) FROM stdin;
\.


--
-- Data for Name: order_reviews; Type: TABLE DATA; Schema: raw; Owner: -
--

COPY raw.order_reviews (review_id, order_id, review_score, review_comment_title, review_comment_message, review_creation_date, review_answer_timestamp, _source_file, _loaded_at) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: raw; Owner: -
--

COPY raw.orders (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at, order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date, _source_file, _loaded_at) FROM stdin;
old1	c-old1	delivered	2018-01-05 00:00:00	\N	\N	\N	\N	\N	2026-10-28 17:05:32.676684+03
old2	c-old2	delivered	2018-01-05 00:00:00	\N	\N	\N	\N	\N	2026-10-28 17:05:32.676684+03
new1	c-new1	delivered	2018-01-12 00:00:00	\N	\N	\N	\N	\N	2026-10-28 17:05:33.070305+03
new2	c-new2	delivered	2018-01-12 00:00:00	\N	\N	\N	\N	\N	2026-10-28 17:05:33.070305+03
\.


--
-- Data for Name: product_category_translation; Type: TABLE DATA; Schema: raw; Owner: -
--

COPY raw.product_category_translation (product_category_name, product_category_name_english, _source_file, _loaded_at) FROM stdin;
A	alpha	\N	2026-10-28 17:05:32.676684+03
B	beta	\N	2026-10-28 17:05:32.676684+03
C	gamma	\N	2026-10-28 17:05:32.676684+03
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: raw; Owner: -
--

COPY raw.products (product_id, product_category_name, product_name_lenght, product_description_lenght, product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm, _source_file, _loaded_at) FROM stdin;
P	A	\N	\N	\N	\N	\N	\N	\N	\N	2026-10-28 17:05:32.676684+03
\.


--
-- Data for Name: sellers; Type: TABLE DATA; Schema: raw; Owner: -
--

COPY raw.sellers (seller_id, seller_zip_code_prefix, seller_city, seller_state, _source_file, _loaded_at) FROM stdin;
S1	\N	\N	\N	\N	2026-10-28 17:05:32.676684+03
S2	\N	\N	\N	\N	2026-10-28 17:05:32.676684+03
\.


--
-- Name: baseline_product baseline_product_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.baseline_product
    ADD CONSTRAINT baseline_product_pkey PRIMARY KEY (baseline_id, product_id);


--
-- Name: baseline_product baseline_product_version_id_key; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.baseline_product
    ADD CONSTRAINT baseline_product_version_id_key UNIQUE (version_id);


--
-- Name: baseline_snapshot baseline_snapshot_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.baseline_snapshot
    ADD CONSTRAINT baseline_snapshot_pkey PRIMARY KEY (baseline_id);


--
-- Name: category_event category_event_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.category_event
    ADD CONSTRAINT category_event_pkey PRIMARY KEY (event_id);


--
-- Name: category_event category_event_supersedes_event_id_key; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.category_event
    ADD CONSTRAINT category_event_supersedes_event_id_key UNIQUE (supersedes_event_id);


--
-- Name: initial_release initial_release_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.initial_release
    ADD CONSTRAINT initial_release_pkey PRIMARY KEY (singleton);


--
-- Name: release_category release_category_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.release_category
    ADD CONSTRAINT release_category_pkey PRIMARY KEY (release_id, category_key);


--
-- Name: release_source_row release_source_row_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.release_source_row
    ADD CONSTRAINT release_source_row_pkey PRIMARY KEY (release_id, source_table, row_hash);


--
-- Name: report_binding report_binding_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_binding
    ADD CONSTRAINT report_binding_pkey PRIMARY KEY (release_id, order_id, order_item_id);


--
-- Name: report_release report_release_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_release
    ADD CONSTRAINT report_release_pkey PRIMARY KEY (release_id);


--
-- Name: report_result report_result_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_result
    ADD CONSTRAINT report_result_pkey PRIMARY KEY (release_id);


--
-- Name: schema_version schema_version_pkey; Type: CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.schema_version
    ADD CONSTRAINT schema_version_pkey PRIMARY KEY (singleton);


--
-- Name: baseline_product history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.baseline_product FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: baseline_snapshot history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.baseline_snapshot FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: category_event history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.category_event FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: initial_release history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.initial_release FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: release_category history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.release_category FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: release_source_row history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.release_source_row FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: report_binding history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.report_binding FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: report_release history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.report_release FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: report_result history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.report_result FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: schema_version history_no_mutation; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_no_mutation BEFORE DELETE OR UPDATE OR TRUNCATE ON history.schema_version FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();


--
-- Name: baseline_product history_seal; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_seal BEFORE INSERT ON history.baseline_product FOR EACH ROW EXECUTE FUNCTION history.immutable_guard();


--
-- Name: release_category history_seal; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_seal BEFORE INSERT ON history.release_category FOR EACH ROW EXECUTE FUNCTION history.immutable_guard();


--
-- Name: release_source_row history_seal; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_seal BEFORE INSERT ON history.release_source_row FOR EACH ROW EXECUTE FUNCTION history.immutable_guard();


--
-- Name: report_binding history_seal; Type: TRIGGER; Schema: history; Owner: -
--

CREATE TRIGGER history_seal BEFORE INSERT ON history.report_binding FOR EACH ROW EXECUTE FUNCTION history.immutable_guard();


--
-- Name: baseline_product baseline_product_baseline_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.baseline_product
    ADD CONSTRAINT baseline_product_baseline_id_fkey FOREIGN KEY (baseline_id) REFERENCES history.baseline_snapshot(baseline_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: category_event category_event_supersedes_event_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.category_event
    ADD CONSTRAINT category_event_supersedes_event_id_fkey FOREIGN KEY (supersedes_event_id) REFERENCES history.category_event(event_id);


--
-- Name: initial_release initial_release_release_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.initial_release
    ADD CONSTRAINT initial_release_release_id_fkey FOREIGN KEY (release_id) REFERENCES history.report_release(release_id);


--
-- Name: release_category release_category_release_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.release_category
    ADD CONSTRAINT release_category_release_id_fkey FOREIGN KEY (release_id) REFERENCES history.report_release(release_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: release_source_row release_source_row_release_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.release_source_row
    ADD CONSTRAINT release_source_row_release_id_fkey FOREIGN KEY (release_id) REFERENCES history.report_release(release_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_binding report_binding_baseline_id_product_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_binding
    ADD CONSTRAINT report_binding_baseline_id_product_id_fkey FOREIGN KEY (baseline_id, product_id) REFERENCES history.baseline_product(baseline_id, product_id);


--
-- Name: report_binding report_binding_event_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_binding
    ADD CONSTRAINT report_binding_event_id_fkey FOREIGN KEY (event_id) REFERENCES history.category_event(event_id);


--
-- Name: report_binding report_binding_release_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_binding
    ADD CONSTRAINT report_binding_release_id_fkey FOREIGN KEY (release_id) REFERENCES history.report_release(release_id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: report_release report_release_baseline_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_release
    ADD CONSTRAINT report_release_baseline_id_fkey FOREIGN KEY (baseline_id) REFERENCES history.baseline_snapshot(baseline_id);


--
-- Name: report_release report_release_parent_release_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_release
    ADD CONSTRAINT report_release_parent_release_id_fkey FOREIGN KEY (parent_release_id) REFERENCES history.report_release(release_id);


--
-- Name: report_result report_result_release_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: -
--

ALTER TABLE ONLY history.report_result
    ADD CONSTRAINT report_result_release_id_fkey FOREIGN KEY (release_id) REFERENCES history.report_release(release_id);


--
-- PostgreSQL database dump complete
--

\unrestrict ASwq91XjwhGkFfeedWghEDnaRSwM5An0989Ftpbg3G8BrYhbjqwR2txDhyfkD8l

