-- Business anomalies are warnings: retain source rows and measured NULL/zero.
-- Structural blockers are in 05_typecheck, PK/FK DDL and 90_checks, and rollback
-- cannot persist their log. Their diagnostics must be captured from stderr.
CREATE TABLE core.data_issues (
    issue_code text NOT NULL,
    severity text NOT NULL CHECK (severity IN ('warning', 'blocker')),
    entity_type text NOT NULL,
    entity_key jsonb NOT NULL,
    details jsonb NOT NULL,
    PRIMARY KEY (issue_code, entity_type, entity_key)
);
COMMENT ON TABLE core.data_issues IS
    'Observed source anomalies, not causal explanations or instructions to delete rows. Failed-build blockers are reported by exceptions and rolled back.';

INSERT INTO core.data_issues
SELECT issue.code, 'warning', 'order', jsonb_build_object('order_id', o.order_id),
       jsonb_build_object('order_status', o.order_status,
           'purchased_at', o.order_purchase_timestamp, 'approved_at', o.order_approved_at,
           'carrier_at', o.order_delivered_carrier_date,
           'delivered_at', o.order_delivered_customer_date,
           'estimated_at', o.order_estimated_delivery_date)
FROM core.fact_order AS o
CROSS JOIN LATERAL (VALUES
    ('delivered_missing_delivery_date', o.order_status = 'delivered' AND o.order_delivered_customer_date IS NULL),
    ('delivered_missing_approval_date', o.order_status = 'delivered' AND o.order_approved_at IS NULL),
    ('delivery_date_on_other_status', o.order_status <> 'delivered' AND o.order_delivered_customer_date IS NOT NULL),
    ('missing_purchase_timestamp', o.order_purchase_timestamp IS NULL),
    ('missing_estimated_delivery_date', o.order_estimated_delivery_date IS NULL),
    ('carrier_before_purchase', o.order_delivered_carrier_date < o.order_purchase_timestamp),
    ('approval_before_purchase', o.order_approved_at < o.order_purchase_timestamp),
    ('carrier_before_approval', o.order_delivered_carrier_date < o.order_approved_at),
    ('delivery_before_carrier', o.order_delivered_customer_date < o.order_delivered_carrier_date),
    ('delivery_before_purchase', o.order_delivered_customer_date < o.order_purchase_timestamp),
    ('unrecognized_order_status', o.order_status NOT IN
        ('delivered', 'shipped', 'canceled', 'unavailable', 'invoiced', 'processing', 'created', 'approved'))
) AS issue(code, present)
WHERE issue.present;

INSERT INTO core.data_issues
SELECT issue.code, 'warning', 'order', jsonb_build_object('order_id', o.order_id),
       jsonb_build_object('order_status', o.order_status, 'missing_child', issue.child)
FROM core.fact_order AS o
CROSS JOIN LATERAL (VALUES
    ('order_without_items', 'items', NOT EXISTS (SELECT FROM core.fact_order_item i WHERE i.order_id = o.order_id)),
    ('order_without_payments', 'payments', NOT EXISTS (SELECT FROM core.fact_payment p WHERE p.order_id = o.order_id)),
    ('order_without_reviews', 'reviews', NOT EXISTS (SELECT FROM core.fact_review r WHERE r.order_id = o.order_id))
) AS issue(code, child, present)
WHERE issue.present;

-- No items/payments and all-NULL amounts stay separate from a measured zero.
WITH items AS (
    SELECT order_id, count(*) AS n, count(price) AS priced,
           count(freight_value) AS freighted, sum(price) AS price,
           sum(freight_value) AS freight
    FROM core.fact_order_item GROUP BY order_id
), payments AS (
    SELECT order_id, count(*) AS n, count(payment_value) AS valued,
           sum(payment_value) AS paid
    FROM core.fact_payment GROUP BY order_id
)
INSERT INTO core.data_issues
SELECT 'payment_item_exact_mismatch', 'warning', 'order', jsonb_build_object('order_id', i.order_id),
       jsonb_build_object('item_count', i.n, 'payment_count', p.n,
           'price', i.price, 'freight', i.freight, 'paid', p.paid,
           'delta_payment_minus_items', p.paid - i.price - i.freight,
           'comparator', 'delta <> 0',
           'also_abs_delta_gt_0_01', abs(p.paid - i.price - i.freight) > 0.01)
FROM items AS i JOIN payments AS p USING (order_id)
WHERE i.priced = i.n AND i.freighted = i.n AND p.valued = p.n
  AND p.paid - i.price - i.freight <> 0;

INSERT INTO core.data_issues
SELECT issue.code, 'warning', 'order_item',
       jsonb_build_object('order_id', i.order_id, 'order_item_id', i.order_item_id),
       jsonb_build_object('price', i.price, 'freight_value', i.freight_value)
FROM core.fact_order_item AS i
CROSS JOIN LATERAL (VALUES
    ('item_missing_price', i.price IS NULL),
    ('item_missing_freight', i.freight_value IS NULL),
    ('item_negative_price', i.price < 0),
    ('item_negative_freight', i.freight_value < 0),
    ('item_zero_price', i.price = 0),
    ('item_price_scale_gt_2', scale(i.price) > 2),
    ('item_freight_scale_gt_2', scale(i.freight_value) > 2),
    ('item_nonpositive_sequence', i.order_item_id <= 0)
) AS issue(code, present)
WHERE issue.present;

INSERT INTO core.data_issues
SELECT issue.code, 'warning', 'payment',
       jsonb_build_object('order_id', p.order_id, 'payment_sequential', p.payment_sequential),
       jsonb_build_object('payment_type', p.payment_type,
           'payment_value', p.payment_value, 'payment_installments', p.payment_installments)
FROM core.fact_payment AS p
CROSS JOIN LATERAL (VALUES
    ('payment_missing_value', p.payment_value IS NULL),
    ('payment_zero_value', p.payment_value = 0),
    ('payment_negative_value', p.payment_value < 0),
    ('payment_value_scale_gt_2', scale(p.payment_value) > 2),
    ('payment_missing_installments', p.payment_installments IS NULL),
    ('payment_nonpositive_installments', p.payment_installments <= 0),
    ('payment_nonpositive_sequence', p.payment_sequential <= 0),
    ('unrecognized_payment_type', p.payment_type IS NULL OR p.payment_type NOT IN
        ('credit_card', 'boleto', 'voucher', 'debit_card'))
) AS issue(code, present)
WHERE issue.present;

INSERT INTO core.data_issues
SELECT issue.code, 'warning', 'review_order',
       jsonb_build_object('review_id', r.review_id, 'order_id', r.order_id),
       jsonb_build_object('review_score', r.review_score,
           'review_creation_date', r.review_creation_date,
           'review_answer_timestamp', r.review_answer_timestamp)
FROM core.fact_review AS r
CROSS JOIN LATERAL (VALUES
    ('review_missing_score', r.review_score IS NULL),
    ('review_score_outside_1_5', r.review_score NOT BETWEEN 1 AND 5),
    ('review_missing_creation_date', r.review_creation_date IS NULL),
    ('review_missing_answer_timestamp', r.review_answer_timestamp IS NULL),
    ('review_answer_before_creation', r.review_answer_timestamp < r.review_creation_date)
) AS issue(code, present)
WHERE issue.present;

-- JSONB preserves NULL positions: NULL-vs-value is a real payload difference.
INSERT INTO core.data_issues
SELECT 'review_id_payload_conflict', 'warning', 'review_id',
       jsonb_build_object('review_id', review_id),
       jsonb_build_object('association_count', count(*), 'distinct_payload_count',
           count(DISTINCT jsonb_build_array(review_score, review_comment_title,
               review_comment_message, review_creation_date, review_answer_timestamp)))
FROM core.fact_review
GROUP BY review_id
HAVING count(DISTINCT jsonb_build_array(review_score, review_comment_title,
    review_comment_message, review_creation_date, review_answer_timestamp)) > 1;

INSERT INTO core.data_issues
SELECT 'product_missing_category', 'warning', 'product',
       jsonb_build_object('product_id', p.product_id),
       jsonb_build_object('category_key', p.category_key)
FROM core.dim_product p JOIN core.dim_category c USING (category_key)
WHERE c.is_unknown;

INSERT INTO core.data_issues
SELECT 'category_missing_translation', 'warning', 'category',
       jsonb_build_object('category_key', c.category_key),
       jsonb_build_object('name_pt', c.name_pt, 'name_en', c.name_en)
FROM core.dim_category c WHERE NOT c.is_unknown AND NOT c.is_translated;

INSERT INTO core.data_issues
SELECT 'product_' || measure.name || '_' || issue.kind, 'warning', 'product',
       jsonb_build_object('product_id', p.product_id),
       jsonb_build_object('column', measure.name, 'value', measure.value)
FROM core.dim_product AS p
CROSS JOIN LATERAL (VALUES
    ('weight_g', p.product_weight_g), ('length_cm', p.product_length_cm),
    ('height_cm', p.product_height_cm), ('width_cm', p.product_width_cm),
    ('name_lenght', p.product_name_lenght::numeric),
    ('description_lenght', p.product_description_lenght::numeric),
    ('photos_qty', p.product_photos_qty::numeric)
) AS measure(name, value)
CROSS JOIN LATERAL (VALUES
    ('missing', measure.value IS NULL), ('zero', measure.value = 0), ('negative', measure.value < 0)
) AS issue(kind, present)
WHERE issue.present;

INSERT INTO core.data_issues
SELECT issue.code, 'warning', source.entity_type, source.entity_key,
       jsonb_build_object('zip_code_prefix_raw', source.zip)
FROM (
    SELECT 'seller' AS entity_type, jsonb_build_object('seller_id', seller_id) AS entity_key,
           seller_zip_code_prefix AS zip FROM core.dim_seller
    UNION ALL
    SELECT 'customer_context', jsonb_build_object('customer_id', customer_id),
           customer_zip_code_prefix FROM core.dim_customer_context
) AS source
CROSS JOIN LATERAL (VALUES
    ('zip_missing', source.zip IS NULL),
    ('zip_invalid_format', source.zip IS NOT NULL AND source.zip !~ '^[0-9]{1,5}$')
) AS issue(code, present)
WHERE issue.present;
