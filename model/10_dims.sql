-- W-08: detail dimensions. Interface: model/CONTRACT.md; mapping: docs/model.md.
-- Run after the build owner creates an empty core schema, in its transaction.
-- No raw writes, destructive reset, transaction control, or silent row selection.

DO $validate_dimension_inputs$
DECLARE
    bad record;
BEGIN
    SELECT * INTO bad
    FROM (
        SELECT 'raw.customers' AS source_table, 'customer_id' AS column_name,
               customer_id AS source_key, customer_id AS source_value
        FROM raw.customers WHERE customer_id IS NULL OR customer_id ~ '^[[:space:]]*$'
        UNION ALL
        SELECT 'raw.customers', 'customer_unique_id', customer_id, customer_unique_id
        FROM raw.customers WHERE customer_unique_id IS NULL OR customer_unique_id ~ '^[[:space:]]*$'
        UNION ALL
        SELECT 'raw.sellers', 'seller_id', seller_id, seller_id
        FROM raw.sellers WHERE seller_id IS NULL OR seller_id ~ '^[[:space:]]*$'
        UNION ALL
        SELECT 'raw.products', 'product_id', product_id, product_id
        FROM raw.products WHERE product_id IS NULL OR product_id ~ '^[[:space:]]*$'
        UNION ALL
        SELECT 'raw.product_category_translation', 'product_category_name',
               product_category_name, product_category_name
        FROM raw.product_category_translation
        WHERE product_category_name IS NULL
    ) AS invalid_keys LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Invalid required identity: %.%, key=%, value=%',
            bad.source_table, bad.column_name, bad.source_key, bad.source_value;
    END IF;

    SELECT p.product_id, v.column_name, v.source_value INTO bad
    FROM raw.products AS p
    CROSS JOIN LATERAL (VALUES
        ('product_name_lenght', p.product_name_lenght),
        ('product_description_lenght', p.product_description_lenght),
        ('product_photos_qty', p.product_photos_qty)
    ) AS v(column_name, source_value)
    WHERE v.source_value IS NOT NULL AND v.source_value !~ '^[+-]?[0-9]+$'
    LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Invalid integer text: raw.products.%, product_id=%, value=%',
            bad.column_name, bad.product_id, bad.source_value;
    END IF;

    SELECT p.product_id, v.column_name, v.source_value INTO bad
    FROM raw.products AS p
    CROSS JOIN LATERAL (VALUES
        ('product_weight_g', p.product_weight_g),
        ('product_length_cm', p.product_length_cm),
        ('product_height_cm', p.product_height_cm),
        ('product_width_cm', p.product_width_cm)
    ) AS v(column_name, source_value)
    WHERE v.source_value IS NOT NULL
      AND v.source_value !~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)$'
    LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Invalid finite numeric text: raw.products.%, product_id=%, value=%',
            bad.column_name, bad.product_id, bad.source_value;
    END IF;
END
$validate_dimension_inputs$;

-- The date dimension covers all event roles, so validate their text BEFORE casting.
-- No offset is guessed; fractional seconds are blocked before any rounding.
-- Shape validation is followed by the PostgreSQL cast (invalid dates/ranges fail).
DO $validate_event_date_inputs$
DECLARE
    bad record;
BEGIN
    SELECT * INTO bad
    FROM (
        SELECT 'raw.orders' AS source_table, o.order_id AS source_key,
               v.column_name, v.source_value
        FROM raw.orders AS o CROSS JOIN LATERAL (VALUES
            ('order_purchase_timestamp', o.order_purchase_timestamp),
            ('order_approved_at', o.order_approved_at),
            ('order_delivered_carrier_date', o.order_delivered_carrier_date),
            ('order_delivered_customer_date', o.order_delivered_customer_date),
            ('order_estimated_delivery_date', o.order_estimated_delivery_date)
        ) AS v(column_name, source_value)
        UNION ALL
        SELECT 'raw.order_items', order_id, 'shipping_limit_date', shipping_limit_date
        FROM raw.order_items
        UNION ALL
        SELECT 'raw.order_reviews', r.review_id || ':' || r.order_id,
               v.column_name, v.source_value
        FROM raw.order_reviews AS r CROSS JOIN LATERAL (VALUES
            ('review_creation_date', r.review_creation_date),
            ('review_answer_timestamp', r.review_answer_timestamp)
        ) AS v(column_name, source_value)
    ) AS event_dates
    WHERE source_value IS NOT NULL
      AND source_value !~ '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01]) ([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$'
    LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Invalid naive timestamp text: %.%, key=%, value=%',
            bad.source_table, bad.column_name, bad.source_key, bad.source_value;
    END IF;
END
$validate_event_date_inputs$;

CREATE TABLE core.dim_date (
    date_day date PRIMARY KEY,
    month_start date NOT NULL,
    year_number integer NOT NULL,
    quarter_number integer NOT NULL CHECK (quarter_number BETWEEN 1 AND 4),
    month_number integer NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    day_of_month integer NOT NULL CHECK (day_of_month BETWEEN 1 AND 31),
    iso_year integer NOT NULL,
    iso_week integer NOT NULL CHECK (iso_week BETWEEN 1 AND 53),
    iso_day_of_week integer NOT NULL CHECK (iso_day_of_week BETWEEN 1 AND 7),
    is_weekend boolean NOT NULL
);

WITH event_dates AS (
    SELECT v.source_value::timestamp without time zone AS event_at
    FROM raw.orders AS o CROSS JOIN LATERAL (VALUES
        (o.order_purchase_timestamp), (o.order_approved_at),
        (o.order_delivered_carrier_date), (o.order_delivered_customer_date),
        (o.order_estimated_delivery_date)
    ) AS v(source_value)
    UNION ALL
    SELECT shipping_limit_date::timestamp without time zone FROM raw.order_items
    UNION ALL
    SELECT review_creation_date::timestamp without time zone FROM raw.order_reviews
    UNION ALL
    SELECT review_answer_timestamp::timestamp without time zone FROM raw.order_reviews
), bounds AS (
    SELECT least(DATE '2016-09-01', min(event_at::date)) AS first_day,
           greatest(DATE '2018-08-31', max(event_at::date)) AS last_day
    FROM event_dates
), days AS (
    -- Integer date arithmetic avoids the timestamptz/DST generate_series overload.
    SELECT b.first_day + s.day_offset AS date_day
    FROM bounds AS b
    CROSS JOIN LATERAL generate_series(0, b.last_day - b.first_day) AS s(day_offset)
)
INSERT INTO core.dim_date (
    date_day, month_start, year_number, quarter_number, month_number,
    day_of_month, iso_year, iso_week, iso_day_of_week, is_weekend
)
SELECT date_day, date_trunc('month', date_day::timestamp)::date,
       extract(year FROM date_day)::integer, extract(quarter FROM date_day)::integer,
       extract(month FROM date_day)::integer, extract(day FROM date_day)::integer,
       extract(isoyear FROM date_day)::integer, extract(week FROM date_day)::integer,
       extract(isodow FROM date_day)::integer, extract(isodow FROM date_day) IN (6, 7)
FROM days;
CREATE INDEX dim_date_month_start_idx ON core.dim_date (month_start);
COMMENT ON TABLE core.dim_date IS
    'Continuous daily calendar across all source event dates and at least Sep2016-Aug2018; no inferred observation horizon.';
COMMENT ON COLUMN core.dim_date.date_day IS 'Date key; join each timestamp role through its date part.';
COMMENT ON COLUMN core.dim_date.month_start IS 'Month grain; select DISTINCT before joining a month aggregate.';

CREATE TABLE core.dim_order_status (
    order_status text PRIMARY KEY CHECK (order_status !~ '^[[:space:]]*$'),
    is_revenue boolean NOT NULL,
    CONSTRAINT order_status_revenue_rule CHECK (is_revenue = (order_status = 'delivered'))
);
INSERT INTO core.dim_order_status (order_status, is_revenue)
SELECT order_status, order_status = 'delivered'
FROM (
    SELECT order_status FROM raw.orders WHERE order_status IS NOT NULL
    UNION
    SELECT known_status FROM (VALUES
        ('delivered'), ('shipped'), ('canceled'), ('unavailable'),
        ('invoiced'), ('processing'), ('created'), ('approved')
    ) AS statuses(known_status)
) AS status_domain;
COMMENT ON TABLE core.dim_order_status IS 'Observed and known status domain; unseen status values are retained and should be reported.';
COMMENT ON COLUMN core.dim_order_status.is_revenue IS 'Assignment item-revenue eligibility: delivered only; not proof of buyout, settlement or no return.';

CREATE TABLE core.dim_customer (
    customer_unique_id text PRIMARY KEY CHECK (customer_unique_id !~ '^[[:space:]]*$')
);
INSERT INTO core.dim_customer (customer_unique_id)
SELECT DISTINCT customer_unique_id FROM raw.customers;
COMMENT ON TABLE core.dim_customer IS 'One observed buyer per customer_unique_id; no selected address or invented history.';

CREATE TABLE core.dim_customer_context (
    customer_id text PRIMARY KEY CHECK (customer_id !~ '^[[:space:]]*$'),
    customer_unique_id text NOT NULL REFERENCES core.dim_customer (customer_unique_id),
    customer_zip_code_prefix text,
    customer_zip_code_prefix_validated text,
    customer_city text,
    customer_state text,
    UNIQUE (customer_id, customer_unique_id),
    CONSTRAINT customer_context_zip_rule CHECK (
        customer_zip_code_prefix_validated IS NOT DISTINCT FROM
        CASE WHEN customer_zip_code_prefix ~ '^[0-9]{1,5}$'
             THEN lpad(customer_zip_code_prefix, 5, '0') END
    )
);
INSERT INTO core.dim_customer_context (
    customer_id, customer_unique_id, customer_zip_code_prefix,
    customer_zip_code_prefix_validated, customer_city, customer_state
)
SELECT customer_id, customer_unique_id, customer_zip_code_prefix,
       CASE WHEN customer_zip_code_prefix ~ '^[0-9]{1,5}$'
            THEN lpad(customer_zip_code_prefix, 5, '0') END,
       customer_city, customer_state
FROM raw.customers;
CREATE INDEX dim_customer_context_buyer_idx ON core.dim_customer_context (customer_unique_id);
COMMENT ON TABLE core.dim_customer_context IS 'All source customer_id contexts, including those without orders; source context is not a buyer address history.';
COMMENT ON COLUMN core.dim_customer_context.customer_zip_code_prefix IS 'Original source text, unchanged, including leading zeros and malformed values.';
COMMENT ON COLUMN core.dim_customer_context.customer_zip_code_prefix_validated IS 'Derived 5-digit prefix only for 1-5 ASCII digits; invalid/NULL source yields NULL without truncation.';

CREATE TABLE core.dim_seller (
    seller_id text PRIMARY KEY CHECK (seller_id !~ '^[[:space:]]*$'),
    seller_zip_code_prefix text,
    seller_zip_code_prefix_validated text,
    seller_city text,
    seller_state text,
    CONSTRAINT seller_zip_rule CHECK (
        seller_zip_code_prefix_validated IS NOT DISTINCT FROM
        CASE WHEN seller_zip_code_prefix ~ '^[0-9]{1,5}$'
             THEN lpad(seller_zip_code_prefix, 5, '0') END
    )
);
INSERT INTO core.dim_seller (
    seller_id, seller_zip_code_prefix, seller_zip_code_prefix_validated, seller_city, seller_state
)
SELECT seller_id, seller_zip_code_prefix,
       CASE WHEN seller_zip_code_prefix ~ '^[0-9]{1,5}$'
            THEN lpad(seller_zip_code_prefix, 5, '0') END,
       seller_city, seller_state
FROM raw.sellers;
COMMENT ON TABLE core.dim_seller IS 'One source seller; city/state and raw ZIP remain untrimmed, uncorrected source text.';
COMMENT ON COLUMN core.dim_seller.seller_zip_code_prefix_validated IS 'Derived 5-digit prefix only for 1-5 ASCII digits; never truncate unexpected text.';

CREATE TABLE core.dim_category (
    category_key text PRIMARY KEY,
    name_pt text UNIQUE,
    name_en text,
    is_unknown boolean NOT NULL,
    is_translated boolean NOT NULL,
    has_translation_row boolean NOT NULL,
    CONSTRAINT category_member_rule CHECK (
        (is_unknown AND category_key = 'unknown' AND name_pt IS NULL
            AND name_en IS NULL AND NOT is_translated AND NOT has_translation_row)
        OR
        (NOT is_unknown AND name_pt IS NOT NULL AND category_key = 'pt:' || name_pt
            AND is_translated = (name_en IS NOT NULL)
            AND (has_translation_row OR name_en IS NULL))
    )
);
INSERT INTO core.dim_category (category_key, name_pt, name_en, is_unknown, is_translated, has_translation_row)
VALUES ('unknown', NULL, NULL, true, false, false);
WITH category_domain AS (
    SELECT product_category_name FROM raw.products WHERE product_category_name IS NOT NULL
    UNION
    SELECT product_category_name FROM raw.product_category_translation
)
INSERT INTO core.dim_category (category_key, name_pt, name_en, is_unknown, is_translated, has_translation_row)
SELECT 'pt:' || c.product_category_name, c.product_category_name,
       t.product_category_name_english, false, t.product_category_name_english IS NOT NULL,
       t.product_category_name IS NOT NULL
FROM category_domain AS c
LEFT JOIN raw.product_category_translation AS t USING (product_category_name);
-- Translation rows are NOT deduplicated: duplicate PT keys fan out here and fail PK.
COMMENT ON TABLE core.dim_category IS 'Union of product and translation domains plus explicit unknown; missing translation never erases a known PT category.';
COMMENT ON COLUMN core.dim_category.category_key IS 'Collision-free discriminator: unknown for NULL source, otherwise pt: concatenated with exact source name.';
COMMENT ON COLUMN core.dim_category.name_pt IS 'Alias of product_category_name; NULL only on unknown member; empty source text stays empty.';
COMMENT ON COLUMN core.dim_category.name_en IS 'Alias of product_category_name_english; NULL remains missing, no fallback translation.';
COMMENT ON COLUMN core.dim_category.is_translated IS 'True exactly when an English source value is present; does not assess translation quality.';
COMMENT ON COLUMN core.dim_category.has_translation_row IS 'Source translation-row membership, preserved separately from nullable English value and category usage.';

CREATE TABLE core.dim_product (
    product_id text PRIMARY KEY CHECK (product_id !~ '^[[:space:]]*$'),
    category_key text NOT NULL REFERENCES core.dim_category (category_key),
    product_name_lenght integer,
    product_description_lenght integer,
    product_photos_qty integer,
    product_weight_g numeric CHECK (product_weight_g NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)),
    product_length_cm numeric CHECK (product_length_cm NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)),
    product_height_cm numeric CHECK (product_height_cm NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)),
    product_width_cm numeric CHECK (product_width_cm NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric))
);
INSERT INTO core.dim_product (
    product_id, category_key, product_name_lenght, product_description_lenght,
    product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm
)
SELECT product_id,
       CASE WHEN product_category_name IS NULL THEN 'unknown' ELSE 'pt:' || product_category_name END,
       product_name_lenght::integer, product_description_lenght::integer,
       product_photos_qty::integer, product_weight_g::numeric, product_length_cm::numeric,
       product_height_cm::numeric, product_width_cm::numeric
FROM raw.products;
CREATE INDEX dim_product_category_idx ON core.dim_product (category_key);
COMMENT ON TABLE core.dim_product IS 'One source product with every business attribute; measurements use exact numeric, zeros/NULL remain distinct.';
COMMENT ON COLUMN core.dim_product.product_name_lenght IS 'Original source spelling; length metadata, not a product name.';
COMMENT ON COLUMN core.dim_product.product_description_lenght IS 'Original source spelling; length metadata, not description text.';
