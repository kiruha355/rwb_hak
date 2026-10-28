-- DESIGN ONLY. NOT EXECUTED. PostgreSQL 16; review before implementation.
-- Persistent objects live in core but OUTSIDE model/00_schemas.sql's drop list.
-- Dedicated migration owner; rebuild role SELECT only on these objects.
-- No durable table references a disposable model table.
-- Content IDs: lowercase SHA256 of canonical UTF-8 payload, NOT serial rebuild IDs.

CREATE TABLE core.category_source_package (
    package_id text PRIMARY KEY CHECK (package_id ~ '^[0-9a-f]{64}$'),
    parent_package_id text REFERENCES core.category_source_package,
    artifact_uri text NOT NULL,
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    recorded_at timestamptz NOT NULL,
    source_kind text NOT NULL CHECK (source_kind IN ('olist_baseline','category_events','catalog_snapshot')),
    metadata jsonb NOT NULL
);

CREATE TABLE core.category_baseline (
    dataset_id text NOT NULL REFERENCES core.category_source_package(package_id),
    product_id text NOT NULL,
    category_key text NOT NULL,
    -- Explicitly unknown, never min(order timestamp), -infinity or 2016-01-01.
    business_valid_from timestamp without time zone CHECK (business_valid_from IS NULL),
    PRIMARY KEY (dataset_id, product_id)
);

CREATE TABLE core.category_event (
    event_id text PRIMARY KEY CHECK (event_id ~ '^[0-9a-f]{64}$'),
    package_id text NOT NULL REFERENCES core.category_source_package,
    source_system text NOT NULL,
    source_event_id text NOT NULL,
    source_revision bigint NOT NULL,
    payload_sha256 text NOT NULL,
    product_id text NOT NULL,
    seller_id text, -- NULL=global product scope, NOT unknown seller
    action text NOT NULL CHECK (action IN ('set','unset_override')),
    category_key text,
    -- UTC receipt clock. Never compared directly to naive Olist timestamps.
    recorded_at timestamptz NOT NULL,
    source_observed_at timestamptz,
    -- Business clock with contract named below, may be unknown.
    business_valid_from timestamp without time zone,
    business_clock_contract text,
    -- If source validity is unknown and policy allows future application:
    policy_apply_from timestamp without time zone,
    policy_clock_contract text,
    supersedes_event_id text UNIQUE REFERENCES core.category_event(event_id),
    authority_ref text NOT NULL, -- authenticated seller/catalog operator evidence
    reason text,
    UNIQUE (source_system, source_event_id, source_revision),
    CHECK ((action='set' AND category_key IS NOT NULL)
        OR (action='unset_override' AND seller_id IS NOT NULL AND category_key IS NULL)),
    CHECK ((business_valid_from IS NULL) = (business_clock_contract IS NULL)),
    CHECK ((policy_apply_from IS NULL) = (policy_clock_contract IS NULL)),
    CHECK (business_valid_from IS NULL OR policy_apply_from IS NULL)
);
-- Ingest procedure additionally verifies same correction scope, acyclic chain,
-- prior committed target, package membership/hash, authority, and time contract.
-- NULL validity AND NULL policy start means retained evidence, not active change.
-- Serialize per logical product (covers product+seller races); retry exact event
-- as no-op, conflicting same source identity as error. Never ON CONFLICT UPDATE.
-- UNIQUE supersedes rejects concurrent correction branches pending resolution.

CREATE TABLE core.category_report_release (
    release_id text PRIMARY KEY CHECK (release_id ~ '^[0-9a-f]{64}$'),
    parent_release_id text REFERENCES core.category_report_release,
    baseline_dataset_id text NOT NULL REFERENCES core.category_source_package,
    release_kind text NOT NULL CHECK (release_kind IN ('original','extension','restatement')),
    manifest jsonb NOT NULL,
    -- manifest pins ALL CSV artifacts, full ordered event-package list,
    -- assignment artifact, category labels/taxonomy, SQL blobs, metric policy,
    -- item population, cutoffs, timestamps/encoding/numeric ordering and output hash.
    recorded_at timestamptz NOT NULL,
    publication_authority_ref text NOT NULL
);

CREATE TABLE core.category_report_binding (
    release_id text NOT NULL REFERENCES core.category_report_release,
    order_id text NOT NULL,
    order_item_id integer NOT NULL,
    product_id text NOT NULL,
    seller_id text NOT NULL,
    source_item_sha256 text NOT NULL, -- compare raw values at load, not row offset
    category_key text NOT NULL,
    baseline_dataset_id text,
    event_id text REFERENCES core.category_event,
    attribution_basis text NOT NULL CHECK (attribution_basis IN
        ('snapshot_at_bootstrap','asserted_valid_time','observed_since_policy','unknown_history')),
    PRIMARY KEY (release_id, order_id, order_item_id),
    FOREIGN KEY (baseline_dataset_id, product_id)
        REFERENCES core.category_baseline(dataset_id, product_id),
    CHECK ((event_id IS NOT NULL)::integer + (baseline_dataset_id IS NOT NULL)::integer = 1)
);
-- Release publication and all bindings commit together AFTER validation.
-- Durable rows are immutable; release extension preserves prior bindings.
-- A new binding/report ID is required for corrections, deletions or late facts.

-- Recreated in model/10_dims.sql, DROP explicitly in 00 before its dependencies.
CREATE TABLE core.dim_category_version (
    version_id text PRIMARY KEY,
    product_id text NOT NULL REFERENCES core.dim_product,
    seller_id text REFERENCES core.dim_seller,
    category_key text NOT NULL REFERENCES core.dim_category,
    event_id text,
    attribution_basis text NOT NULL,
    business_valid_from timestamp without time zone,
    policy_apply_from timestamp without time zone
);
-- Version ID includes baseline dataset/product OR event ID; no nextval() identity.
-- Populate dim_category using pinned raw + retained version category domain and
-- pinned taxonomy labels. Retain baseline categories even when not used today.
-- dim_product.category_key remains an explicitly documented baseline attribute.

-- model/20_facts.sql adds this at CREATE TABLE time, then loads a pinned release:
-- category_version_id text NOT NULL REFERENCES core.dim_category_version(version_id)
-- Join binding on (release_id, order_id, order_item_id), validate product/seller
-- and exact item payload hash, require exactly one binding per source item.
-- Reject missing/extra binding, never hide it with an INNER JOIN filter.

-- model/40_mart.sql: category follows the item-bound version:
-- JOIN core.dim_category_version v ON v.version_id=i.category_version_id
-- JOIN core.dim_category c ON c.category_key=v.category_key
-- A separate explicitly named current-category view may use current resolver.

-- Recommended optional projection: materialize normalized [from,to) intervals
-- PER release + clock kind + scope, excluding baseline rows with unknown start.
-- Verify no same-scope overlaps by lag(to); do not compare product intervals
-- against seller intervals, whose overlap is intentional precedence.
-- An EXCLUDE USING gist extension-based variant is optional, not needed here.
-- Both durable and derived constraints need actual PG16 integration tests.

-- Role plan (performed by DB administrator, not ordinary rebuild):
-- raw owned by raw_owner; persistent tables owned by category_history_owner;
-- rebuild role is neither owner/member nor superuser, has no raw DML/DDL rights.
-- Grant rebuild SELECT on raw and durable tables and REFERENCES where required;
-- grant ownership/DDL ONLY for named disposable tables, never durable ownership.
-- Ingest via checked function owned by category_history_owner; PUBLIC EXECUTE
-- revoked, fixed search_path, narrow role grant. No caller-controlled SQL names.
-- DB superuser always remains outside this protection boundary.
