-- W-08: four independent detail grains. Run after 10_dims.sql, in build transaction.
-- Orders are never filtered by child existence. No sums, allocation or dedup here.

DO $validate_fact_inputs$
DECLARE
    bad record;
BEGIN
    SELECT * INTO bad
    FROM (
        SELECT 'raw.orders' AS source_table, o.order_id AS source_key,
               v.column_name, v.source_value
        FROM raw.orders AS o CROSS JOIN LATERAL (VALUES
            ('order_id', o.order_id), ('customer_id', o.customer_id), ('order_status', o.order_status)
        ) AS v(column_name, source_value)
        UNION ALL
        SELECT 'raw.order_items', i.order_id, v.column_name, v.source_value
        FROM raw.order_items AS i CROSS JOIN LATERAL (VALUES
            ('order_id', i.order_id), ('order_item_id', i.order_item_id),
            ('product_id', i.product_id), ('seller_id', i.seller_id)
        ) AS v(column_name, source_value)
        UNION ALL
        SELECT 'raw.order_payments', p.order_id, v.column_name, v.source_value
        FROM raw.order_payments AS p CROSS JOIN LATERAL (VALUES
            ('order_id', p.order_id), ('payment_sequential', p.payment_sequential)
        ) AS v(column_name, source_value)
        UNION ALL
        SELECT 'raw.order_reviews', r.review_id, v.column_name, v.source_value
        FROM raw.order_reviews AS r CROSS JOIN LATERAL (VALUES
            ('review_id', r.review_id), ('order_id', r.order_id)
        ) AS v(column_name, source_value)
    ) AS identities
    WHERE source_value IS NULL OR btrim(source_value) = '' LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Invalid required identity: %.%, key=%, value=%',
            bad.source_table, bad.column_name, bad.source_key, bad.source_value;
    END IF;

    SELECT * INTO bad
    FROM (
        SELECT 'raw.order_items' AS source_table, order_id AS source_key,
               'order_item_id' AS column_name, order_item_id AS source_value
        FROM raw.order_items
        UNION ALL
        SELECT 'raw.order_payments', p.order_id, v.column_name, v.source_value
        FROM raw.order_payments AS p CROSS JOIN LATERAL (VALUES
            ('payment_sequential', p.payment_sequential), ('payment_installments', p.payment_installments)
        ) AS v(column_name, source_value)
        UNION ALL
        SELECT 'raw.order_reviews', review_id || ':' || order_id, 'review_score', review_score
        FROM raw.order_reviews
    ) AS integer_inputs
    WHERE source_value IS NOT NULL AND source_value !~ '^[+-]?[0-9]+$'
    LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Invalid integer text: %.%, key=%, value=%',
            bad.source_table, bad.column_name, bad.source_key, bad.source_value;
    END IF;

    SELECT * INTO bad
    FROM (
        SELECT 'raw.order_items' AS source_table, i.order_id AS source_key,
               v.column_name, v.source_value
        FROM raw.order_items AS i CROSS JOIN LATERAL (VALUES
            ('price', i.price), ('freight_value', i.freight_value)
        ) AS v(column_name, source_value)
        UNION ALL
        SELECT 'raw.order_payments', order_id, 'payment_value', payment_value
        FROM raw.order_payments
    ) AS numeric_inputs
    WHERE source_value IS NOT NULL
      AND source_value !~ '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)$'
    LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION 'Invalid finite numeric text: %.%, key=%, value=%',
            bad.source_table, bad.column_name, bad.source_key, bad.source_value;
    END IF;
END
$validate_fact_inputs$;

CREATE TABLE core.fact_order (
    order_id text PRIMARY KEY CHECK (btrim(order_id) <> ''),
    customer_id text NOT NULL CHECK (btrim(customer_id) <> ''),
    customer_unique_id text NOT NULL REFERENCES core.dim_customer (customer_unique_id),
    order_status text NOT NULL REFERENCES core.dim_order_status (order_status),
    order_purchase_timestamp timestamp without time zone,
    order_approved_at timestamp without time zone,
    order_delivered_carrier_date timestamp without time zone,
    order_delivered_customer_date timestamp without time zone,
    order_estimated_delivery_date timestamp without time zone,
    customer_zip_code_prefix text,
    customer_zip_code_prefix_validated text,
    customer_city text,
    customer_state text,
    FOREIGN KEY (customer_id, customer_unique_id)
        REFERENCES core.dim_customer_context (customer_id, customer_unique_id),
    CONSTRAINT order_zip_rule CHECK (
        customer_zip_code_prefix_validated IS NOT DISTINCT FROM
        CASE WHEN customer_zip_code_prefix ~ '^[0-9]{1,5}$'
             THEN lpad(customer_zip_code_prefix, 5, '0') END
    )
);
INSERT INTO core.fact_order (
    order_id, customer_id, customer_unique_id, order_status,
    order_purchase_timestamp, order_approved_at, order_delivered_carrier_date,
    order_delivered_customer_date, order_estimated_delivery_date,
    customer_zip_code_prefix, customer_zip_code_prefix_validated, customer_city, customer_state
)
SELECT o.order_id, o.customer_id, c.customer_unique_id, o.order_status,
       o.order_purchase_timestamp::timestamp without time zone,
       o.order_approved_at::timestamp without time zone,
       o.order_delivered_carrier_date::timestamp without time zone,
       o.order_delivered_customer_date::timestamp without time zone,
       o.order_estimated_delivery_date::timestamp without time zone,
       c.customer_zip_code_prefix, c.customer_zip_code_prefix_validated,
       c.customer_city, c.customer_state
FROM raw.orders AS o
LEFT JOIN core.dim_customer_context AS c ON c.customer_id = o.customer_id;
-- Missing context fails NOT NULL/FK rather than disappearing through INNER JOIN.
CREATE INDEX fact_order_buyer_idx ON core.fact_order (customer_unique_id);
CREATE INDEX fact_order_context_idx ON core.fact_order (customer_id, customer_unique_id);
CREATE INDEX fact_order_status_purchase_idx ON core.fact_order (order_status, order_purchase_timestamp);
CREATE INDEX fact_order_purchase_idx ON core.fact_order (order_purchase_timestamp);
COMMENT ON TABLE core.fact_order IS 'One row per source order, including no-item/no-payment/no-review orders; independent child aggregates belong in mart.';
COMMENT ON COLUMN core.fact_order.customer_id IS 'Source order context identifier; not the buyer identity.';
COMMENT ON COLUMN core.fact_order.customer_unique_id IS 'Observed buyer identity through customer_id; address remains order-specific.';
COMMENT ON COLUMN core.fact_order.customer_zip_code_prefix IS 'Unmodified ZIP text from this order customer context, not a current buyer address.';
COMMENT ON COLUMN core.fact_order.order_purchase_timestamp IS 'Naive source purchase timestamp; NULL preserved; timezone not supplied by source.';
COMMENT ON COLUMN core.fact_order.order_approved_at IS 'Naive source approval timestamp; source name retained; no payment settlement inferred.';
COMMENT ON COLUMN core.fact_order.order_delivered_carrier_date IS 'Naive source handover timestamp at order grain; chronology anomalies are warnings.';
COMMENT ON COLUMN core.fact_order.order_delivered_customer_date IS 'Naive source delivery timestamp; delivered status is not proof of buyout or no return.';
COMMENT ON COLUMN core.fact_order.order_estimated_delivery_date IS 'Naive source delivery promise timestamp; day-vs-timestamp late rule belongs in named mart variants.';

CREATE TABLE core.fact_order_item (
    order_id text NOT NULL REFERENCES core.fact_order (order_id),
    order_item_id integer NOT NULL,
    product_id text NOT NULL REFERENCES core.dim_product (product_id),
    seller_id text NOT NULL REFERENCES core.dim_seller (seller_id),
    price numeric CHECK (price NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)),
    freight_value numeric CHECK (freight_value NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)),
    shipping_limit_at timestamp without time zone,
    PRIMARY KEY (order_id, order_item_id)
);
INSERT INTO core.fact_order_item (
    order_id, order_item_id, product_id, seller_id, price, freight_value, shipping_limit_at
)
SELECT order_id, order_item_id::integer, product_id, seller_id,
       price::numeric, freight_value::numeric, shipping_limit_date::timestamp without time zone
FROM raw.order_items;
CREATE INDEX fact_order_item_product_idx ON core.fact_order_item (product_id);
CREATE INDEX fact_order_item_seller_order_idx ON core.fact_order_item (seller_id, order_id);
COMMENT ON TABLE core.fact_order_item IS 'One source item row / observed unit, keyed by order and within-order ordinal; no allocated order-level payment/review.';
COMMENT ON COLUMN core.fact_order_item.price IS 'Exact source item amount, excluding freight; NULL and measured zero differ; no source scale rounding.';
COMMENT ON COLUMN core.fact_order_item.freight_value IS 'Exact source item freight amount; NULL never replaced with zero.';
COMMENT ON COLUMN core.fact_order_item.shipping_limit_at IS 'Explicit alias of raw.order_items.shipping_limit_date; naive timestamp, no order deadline aggregation implied.';

CREATE TABLE core.fact_payment (
    order_id text NOT NULL REFERENCES core.fact_order (order_id),
    payment_sequential integer NOT NULL,
    payment_type text,
    payment_installments integer,
    payment_value numeric CHECK (payment_value NOT IN ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)),
    PRIMARY KEY (order_id, payment_sequential)
);
INSERT INTO core.fact_payment (
    order_id, payment_sequential, payment_type, payment_installments, payment_value
)
SELECT order_id, payment_sequential::integer, payment_type,
       payment_installments::integer, payment_value::numeric
FROM raw.order_payments;
CREATE INDEX fact_payment_type_idx ON core.fact_payment (payment_type);
COMMENT ON TABLE core.fact_payment IS 'One source payment row per order/payment_sequential, independent of item/review multiplicities.';
COMMENT ON COLUMN core.fact_payment.payment_installments IS 'Source count, including observed zero; not an installment schedule or a dated cash-flow event.';
COMMENT ON COLUMN core.fact_payment.payment_value IS 'Exact source payment amount; no reconciliation adjustment, allocation, zero substitution or scale rounding.';

CREATE TABLE core.fact_review (
    review_id text NOT NULL CHECK (btrim(review_id) <> ''),
    order_id text NOT NULL REFERENCES core.fact_order (order_id),
    review_score integer,
    review_comment_title text,
    review_comment_message text,
    review_creation_date timestamp without time zone,
    review_answer_timestamp timestamp without time zone,
    PRIMARY KEY (review_id, order_id)
);
INSERT INTO core.fact_review (
    review_id, order_id, review_score, review_comment_title, review_comment_message,
    review_creation_date, review_answer_timestamp
)
SELECT review_id, order_id, review_score::integer, review_comment_title, review_comment_message,
       review_creation_date::timestamp without time zone,
       review_answer_timestamp::timestamp without time zone
FROM raw.order_reviews;
CREATE INDEX fact_review_order_idx ON core.fact_review (order_id);
COMMENT ON TABLE core.fact_review IS 'One complete source review-order pair; review_id alone is not unique; conflicting payload across pairs is preserved, never selected away.';
COMMENT ON COLUMN core.fact_review.review_score IS 'Source rating, nullable; unusual values are quality warnings, not silently discarded or NPS.';
COMMENT ON COLUMN core.fact_review.review_comment_title IS 'Full source text without trimming, truncation, empty-string substitution or dedup selection.';
COMMENT ON COLUMN core.fact_review.review_comment_message IS 'Full source text without trimming, truncation, empty-string substitution or dedup selection.';
COMMENT ON COLUMN core.fact_review.review_creation_date IS 'Naive source timestamp retained at timestamp precision despite the source column suffix date.';
COMMENT ON COLUMN core.fact_review.review_answer_timestamp IS 'Naive source response timestamp; latest does not establish authoritative/current opinion.';
