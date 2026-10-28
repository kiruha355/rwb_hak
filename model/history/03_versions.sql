CREATE TABLE core.model_release (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    release_id text NOT NULL REFERENCES history.report_release
);
INSERT INTO core.model_release VALUES(true,current_setting('capibara.report_release'));
CREATE TABLE core.dim_category_version (
    version_id text PRIMARY KEY,
    product_id text NOT NULL REFERENCES core.dim_product,
    seller_id text REFERENCES core.dim_seller,
    category_key text NOT NULL REFERENCES core.dim_category,
    attribution_basis text NOT NULL,
    baseline_id text,
    event_id text REFERENCES history.category_event,
    business_valid_from timestamp,
    policy_apply_from timestamp
);
INSERT INTO core.dim_category_version
SELECT DISTINCT b.version_id,b.product_id,e.seller_id,b.category_key,b.attribution_basis,
    b.baseline_id,b.event_id,e.business_valid_from,e.policy_apply_from
FROM history.report_binding b JOIN core.model_release r USING(release_id)
LEFT JOIN history.category_event e ON e.event_id=b.event_id;
COMMENT ON COLUMN core.dim_product.category_key IS
    'Source product snapshot category; historical item reports use their pinned category_version_id.';
COMMENT ON TABLE core.dim_category_version IS
    'Stable source-derived identities referenced by a pinned release, not inferred Olist as-of history. Baseline business time is unknown.';
