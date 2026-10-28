-- Persistent source, never in the disposable core/mart DROP graph. PG16 only.
-- Trusted offline SQL interface, SECURITY INVOKER; no authorization service.
CREATE SCHEMA IF NOT EXISTS history;
CREATE TABLE IF NOT EXISTS history.schema_version (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    version integer NOT NULL CHECK (version = 1)
);
INSERT INTO history.schema_version VALUES (true, 1) ON CONFLICT DO NOTHING;

CREATE OR REPLACE FUNCTION history.digest(value jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path = pg_catalog
AS $$ SELECT encode(sha256(convert_to(value::text, 'UTF8')), 'hex') $$;

-- Business payload only. Loader receipt/path is not a business attribute.
-- Row hash + multiplicity preserves NULLs, text spelling and duplicate rows.
CREATE OR REPLACE FUNCTION history.source_rows()
RETURNS TABLE (source_table text, row_hash text, occurrences bigint)
LANGUAGE plpgsql STABLE SET search_path = pg_catalog AS $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['orders','order_items','order_payments','order_reviews',
        'products','sellers','customers','product_category_translation'] LOOP
        RETURN QUERY EXECUTE format(
            'SELECT %L, history.digest(to_jsonb(r)-''_loaded_at''-''_source_file''), count(*)
             FROM raw.%I r GROUP BY 2', t, t);
    END LOOP;
END $$;

CREATE TABLE IF NOT EXISTS history.baseline_snapshot (
    baseline_id text PRIMARY KEY,
    captured_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    business_valid_from timestamp CHECK (business_valid_from IS NULL),
    basis text NOT NULL DEFAULT 'snapshot_at_bootstrap' CHECK (basis='snapshot_at_bootstrap')
);
CREATE TABLE IF NOT EXISTS history.baseline_product (
    baseline_id text NOT NULL REFERENCES history.baseline_snapshot DEFERRABLE INITIALLY DEFERRED,
    product_id text NOT NULL,
    category_key text NOT NULL CHECK (category_key='unknown' OR category_key LIKE 'pt:%'),
    version_id text NOT NULL UNIQUE,
    PRIMARY KEY (baseline_id, product_id)
);
CREATE TABLE IF NOT EXISTS history.category_event (
    event_id text PRIMARY KEY CHECK (event_id <> ''),
    product_id text NOT NULL CHECK (product_id <> ''),
    seller_id text CHECK (seller_id <> ''), -- NULL = product scope
    action text NOT NULL CHECK (action IN ('set','unset_override')),
    category_key text CHECK (category_key='unknown' OR category_key LIKE 'pt:%'),
    business_valid_from timestamp,
    policy_apply_from timestamp,
    clock_contract text,
    supersedes_event_id text UNIQUE REFERENCES history.category_event,
    provenance jsonb NOT NULL CHECK (jsonb_typeof(provenance)='object' AND provenance <> '{}'),
    payload_sha256 text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK ((action='set' AND category_key IS NOT NULL)
        OR (action='unset_override' AND seller_id IS NOT NULL AND category_key IS NULL)),
    CHECK (business_valid_from IS NULL OR policy_apply_from IS NULL),
    CHECK (CASE WHEN coalesce(business_valid_from,policy_apply_from) IS NOT NULL
        THEN clock_contract IS NOT DISTINCT FROM 'source_naive_purchase_v1'
        ELSE clock_contract IS NULL END),
    CHECK (isfinite(business_valid_from) AND isfinite(policy_apply_from))
);
CREATE TABLE IF NOT EXISTS history.report_release (
    release_id text PRIMARY KEY CHECK (release_id <> ''),
    parent_release_id text REFERENCES history.report_release,
    release_kind text NOT NULL CHECK (release_kind IN ('original','extension','restatement')),
    baseline_id text NOT NULL REFERENCES history.baseline_snapshot,
    event_ids text[] NOT NULL,
    closed_before timestamp NOT NULL CHECK (isfinite(closed_before)),
    source_digest text NOT NULL,
    binding_digest text NOT NULL,
    taxonomy_digest text NOT NULL,
    policy_version text NOT NULL CHECK (policy_version='category_binding_v1'),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK ((release_kind='original') = (parent_release_id IS NULL))
);
CREATE TABLE IF NOT EXISTS history.release_source_row (
    release_id text NOT NULL REFERENCES history.report_release DEFERRABLE INITIALLY DEFERRED,
    source_table text NOT NULL,
    row_hash text NOT NULL,
    occurrences bigint NOT NULL CHECK (occurrences>0),
    PRIMARY KEY (release_id, source_table, row_hash)
);
CREATE TABLE IF NOT EXISTS history.report_binding (
    release_id text NOT NULL REFERENCES history.report_release DEFERRABLE INITIALLY DEFERRED,
    order_id text NOT NULL,
    order_item_id integer NOT NULL,
    product_id text NOT NULL,
    seller_id text NOT NULL,
    source_item_sha256 text NOT NULL,
    version_id text NOT NULL,
    category_key text NOT NULL,
    attribution_basis text NOT NULL CHECK (attribution_basis IN
        ('snapshot_at_bootstrap','asserted_valid_time','observed_since_policy')),
    baseline_id text,
    event_id text REFERENCES history.category_event,
    PRIMARY KEY (release_id, order_id, order_item_id),
    FOREIGN KEY (baseline_id,product_id) REFERENCES history.baseline_product(baseline_id,product_id),
    CHECK ((baseline_id IS NULL) <> (event_id IS NULL))
);
CREATE TABLE IF NOT EXISTS history.release_category (
    release_id text NOT NULL REFERENCES history.report_release DEFERRABLE INITIALLY DEFERRED,
    category_key text NOT NULL,
    name_pt text,
    name_en text,
    is_unknown boolean NOT NULL,
    is_translated boolean NOT NULL,
    has_translation_row boolean NOT NULL,
    PRIMARY KEY (release_id, category_key),
    CHECK ((is_unknown AND category_key='unknown' AND name_pt IS NULL AND name_en IS NULL
        AND NOT is_translated AND NOT has_translation_row)
        OR (NOT is_unknown AND name_pt IS NOT NULL AND category_key='pt:'||name_pt
        AND is_translated=(name_en IS NOT NULL) AND (has_translation_row OR name_en IS NULL)))
);
CREATE TABLE IF NOT EXISTS history.initial_release (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    release_id text NOT NULL REFERENCES history.report_release
);

-- Seal source manifests by inserting their header LAST, in the same transaction.
-- UPDATE/DELETE/TRUNCATE always fail. A committed header rejects later child INSERT.
-- Owner/superuser can disable triggers: these are invariant guards, not a security boundary.
CREATE OR REPLACE FUNCTION history.immutable_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
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
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['schema_version','baseline_snapshot','baseline_product',
        'category_event','report_release','release_source_row','report_binding',
        'release_category','initial_release'] LOOP
        IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid=format('history.%I',t)::regclass
            AND tgname='history_no_mutation') THEN
            EXECUTE format('CREATE TRIGGER history_no_mutation BEFORE UPDATE OR DELETE OR TRUNCATE ON history.%I
                FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard()',t);
        END IF;
        IF t IN ('baseline_product','release_source_row','report_binding','release_category')
           AND NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid=format('history.%I',t)::regclass
            AND tgname='history_seal') THEN
            EXECUTE format('CREATE TRIGGER history_seal BEFORE INSERT ON history.%I
                FOR EACH ROW EXECUTE FUNCTION history.immutable_guard()',t);
        END IF;
    END LOOP;
END $$;

CREATE OR REPLACE FUNCTION history.append_event(
    p_id text, p_product text, p_seller text, p_action text, p_category text,
    p_valid_from timestamp, p_policy_from timestamp, p_clock text,
    p_supersedes text, p_provenance jsonb) RETURNS text
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
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

CREATE OR REPLACE FUNCTION history.capture_baseline() RETURNS text
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
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

-- Events visible to one release. Corrections are applied only AFTER restricting
-- to its exact ID set. An unset seller event reveals the current product fallback.
CREATE OR REPLACE FUNCTION history.resolve_category(
    p_baseline text, p_events text[], p_product text, p_seller text, p_purchase timestamp)
RETURNS TABLE(version_id text, category_key text, attribution_basis text, baseline_id text, event_id text)
LANGUAGE plpgsql STABLE SET search_path = pg_catalog AS $$
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

CREATE OR REPLACE FUNCTION history.create_release(
    p_id text, p_kind text, p_parent text, p_events text[], p_closed_before timestamp)
RETURNS text LANGUAGE plpgsql SET search_path = pg_catalog AS $$
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

CREATE OR REPLACE FUNCTION history.assert_source() RETURNS void
LANGUAGE plpgsql STABLE SET search_path = pg_catalog AS $$
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

CREATE OR REPLACE FUNCTION history.assert_release(p_id text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path = pg_catalog AS $$
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

-- First successful materialization pins Q1-Q10 output content. Later builds of
-- that same release must reproduce it; policy changes require another release.
CREATE TABLE IF NOT EXISTS history.report_result (
    release_id text PRIMARY KEY REFERENCES history.report_release,
    result_manifest jsonb NOT NULL
);
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_trigger WHERE tgrelid='history.report_result'::regclass
        AND tgname='history_no_mutation') THEN
        CREATE TRIGGER history_no_mutation BEFORE UPDATE OR DELETE OR TRUNCATE ON history.report_result
            FOR EACH STATEMENT EXECUTE FUNCTION history.immutable_guard();
    END IF;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA history FROM PUBLIC;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA history FROM PUBLIC;
