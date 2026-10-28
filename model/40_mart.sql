-- W-10. PostgreSQL 16; run after 10_dims/20_facts inside the build transaction.
-- This fragment owns no transaction, reset, raw read or regression constants.
-- Interface: model/CONTRACT.md. Runtime status: not executed from core.

CREATE TABLE mart.metric_definitions (
    name text PRIMARY KEY,
    grain text NOT NULL,
    formula_sql text NOT NULL,
    status_rule text NOT NULL,
    time_basis text NOT NULL,
    "window" text NOT NULL,
    denominator text NOT NULL,
    null_policy text NOT NULL,
    unit text NOT NULL,
    additive_over text NOT NULL,
    non_additive_over text NOT NULL,
    description text NOT NULL
);

-- These are definitions, not materialized answer values or expected totals.
INSERT INTO mart.metric_definitions VALUES
('orders_placed', 'order', 'count(order_id)', 'all statuses',
 'order_purchase_timestamp', '[2016-09-01,2018-09-01)', 'none',
 'empty calendar month=0', 'orders', 'disjoint order sets; purchase months',
 'overlapping seller/category groups', 'Q1 placed orders; not a delivery event count'),
('orders_delivered', 'order', 'count(order_id) FILTER (WHERE is_delivered)',
 'order_status=delivered', 'order_purchase_timestamp', '[2016-09-01,2018-09-01)',
 'none', 'empty calendar month=0', 'orders', 'disjoint order sets; purchase months',
 'overlapping seller/category groups', 'Delivered status grouped by purchase month'),
('item_revenue', 'item', 'sum(price) with complete price coverage',
 'dim_order_status.is_revenue', 'order_purchase_timestamp',
 'Q1:[2016-09-01,2018-09-01); Q2/Q5:all snapshot', 'none',
 'nonempty population with missing price=NULL; empty calendar month=0', 'BRL',
 'disjoint item sets; item seller; item category; purchase month',
 'repeated order measures; mixed populations', 'Item price excluding freight; delivered is not buyout'),
('seller_orders_delivered', 'seller/order', 'count(DISTINCT order_id) FILTER (WHERE is_delivered)',
 'order_status=delivered', 'order_purchase_timestamp', 'all snapshot', 'none',
 'no matching items=0', 'orders', 'disjoint order sets within a seller',
 'sellers; categories', 'An order with two sellers is counted once for each seller'),
('seller_units_delivered', 'seller/item', 'count(*) FILTER (WHERE is_delivered)',
 'order_status=delivered', 'order_purchase_timestamp', 'all snapshot', 'none',
 'no matching items=0', 'item units', 'disjoint item sets; sellers', 'overlapping sets',
 'One source item row is one observed unit'),
('seller_orders_all_statuses', 'seller/order', 'count(DISTINCT order_id)', 'all statuses',
 'order_purchase_timestamp', 'all snapshot', 'none', 'no matching items=0', 'orders',
 'disjoint order sets within a seller', 'sellers; categories', 'Separate population from delivered revenue'),
('seller_units_all_statuses', 'seller/item', 'count(*)', 'all statuses',
 'order_purchase_timestamp', 'all snapshot', 'none', 'no matching items=0', 'item units',
 'disjoint item sets; sellers', 'overlapping sets', 'All-status observed item rows'),
('order_gmv', 'order', 'sum(price + freight_value) with complete item components',
 'all in v_orders; delivered in Q3', 'order_purchase_timestamp', 'all snapshot', 'none',
 'no items or any unknown component=NULL', 'BRL', 'disjoint order sets',
 'item/seller/category rows repeating order total', 'Item value plus freight; not payment amount'),
('avg_order_gmv', 'order', 'sum(order_gmv) / nullif(count(order_gmv),0)',
 'order_status=delivered', 'order_purchase_timestamp', 'all snapshot',
 'n_order_gmv: delivered orders with complete nonempty item components',
 'no eligible values=NULL; excluded orders counted', 'BRL/order', 'none',
 'every average: recompute numerator/denominator', 'Q3 item-plus-freight order average'),
('avg_payment_amount', 'order', 'sum(payment_amount) / nullif(count(payment_amount),0)',
 'order_status=delivered', 'order_purchase_timestamp', 'all snapshot',
 'n_payment_amount: delivered orders with complete nonempty payments',
 'no payments or incomplete payment amount=NULL', 'BRL/order', 'none',
 'every average; do not reuse n_order_gmv', 'Q3 comparator; installments are not dated cash-flow events'),
('avg_source_rows', 'order', 'sum(source_rows_count)::numeric / nullif(count(*),0)',
 'order_status=delivered', 'order_purchase_timestamp', 'all snapshot', 'all delivered orders',
 'no items=0 rows; no delivered orders=NULL average', 'source rows/order', 'none',
 'every average', 'Counts original item rows, not distinct product/seller groups'),
('avg_units', 'order', 'sum(units_count)::numeric / nullif(count(*),0)',
 'order_status=delivered', 'order_purchase_timestamp', 'all snapshot', 'all delivered orders',
 'no items=0 units; no delivered orders=NULL average', 'item units/order', 'none',
 'every average', 'Equals avg_source_rows because source has no quantity column'),
('avg_distinct_product_seller_lines', 'order',
 'sum(distinct_product_seller_lines_count)::numeric / nullif(count(*),0)',
 'order_status=delivered', 'order_purchase_timestamp', 'all snapshot', 'all delivered orders',
 'no items=0 groups; no delivered orders=NULL average', 'product/seller groups/order', 'none',
 'every average', 'Separate from avg_source_rows and avg_units'),
('buyers_all_snapshot', 'buyer', 'count(DISTINCT customer_unique_id)', 'all statuses',
 'observed orders, not lifetime', 'all snapshot', 'none', 'empty population=0', 'buyers',
 'disjoint buyer sets only', 'months; states; sellers; categories', 'Buyer identity is customer_unique_id'),
('repeat_buyers_all_snapshot', 'buyer', 'count buyers with count(order_id)>1', 'all statuses',
 'observed orders, not lifetime', 'all snapshot', 'none', 'empty population=0', 'buyers',
 'disjoint buyer sets under unchanged observation window', 'time partitions; overlapping groups',
 'Absolute buyers with at least two observed orders, not repeat order count'),
('repeat_buyer_pct_all_snapshot', 'buyer', '100 * repeat_buyers::numeric / nullif(buyers,0)',
 'all statuses', 'observed orders, not lifetime', 'all snapshot', 'buyers_all_snapshot',
 'zero buyers=NULL', 'percent', 'none', 'all slices: recompute buyer grouping',
 'Not retention; no observation completeness or lifetime history inferred'),
('buyers_q1_window', 'buyer', 'count buyers after order-window filter', 'all statuses',
 'order_purchase_timestamp', '[2016-09-01,2018-09-01)', 'none', 'empty population=0', 'buyers',
 'disjoint buyer sets only', 'months; states; sellers; categories', 'Named Q4 window alternative'),
('repeat_buyers_q1_window', 'buyer', 'count buyers with >1 orders inside window', 'all statuses',
 'order_purchase_timestamp', '[2016-09-01,2018-09-01)', 'none', 'empty population=0', 'buyers',
 'disjoint buyer sets under this window', 'time partitions; overlapping groups',
 'Repeat criterion is recomputed within the window'),
('repeat_buyer_pct_q1_window', 'buyer', '100 * repeat_buyers::numeric / nullif(buyers,0)',
 'all statuses', 'order_purchase_timestamp', '[2016-09-01,2018-09-01)', 'buyers_q1_window',
 'zero buyers=NULL', 'percent', 'none', 'all slices: recompute buyer grouping', 'Q4 alternative, not retention'),
('category_item_revenue', 'item/category', 'sum(price) with complete price coverage',
 'dim_order_status.is_revenue', 'order_purchase_timestamp', 'all snapshot', 'none',
 'empty category=0; incomplete price=NULL; unknown category retained', 'BRL',
 'disjoint item categories', 'order totals repeated on categories', 'Missing category differs from missing translation'),
('category_revenue_pct', 'item/category', '100 * category_item_revenue / nullif(total_item_revenue,0)',
 'dim_order_status.is_revenue', 'order_purchase_timestamp', 'all snapshot',
 'total_item_revenue from same population with complete coverage',
 'zero/unknown total=NULL', 'percent', 'one exhaustive disjoint category partition only',
 'different populations; overlapping classifications', 'Return numerator, denominator and coverage'),
('payment_delta', 'order', 'payment_amount - order_gmv', 'all statuses; status retained',
 'no payment event timestamp; purchase context only', 'all snapshot',
 'comparable orders: both sides present and all monetary components known',
 'missing side/any unknown component=NULL; measured zero preserved', 'BRL', 'disjoint comparable order sets',
 'non-comparable orders; item rows', 'Sign is payments minus item-plus-freight'),
('payment_delta_nonzero_exact', 'order', 'payment_delta <> 0; count, sum(delta), sum(abs(delta))',
 'all statuses; status retained', 'no payment event timestamp', 'all snapshot', 'comparable orders',
 'non-comparable predicate=NULL; empty selected set count and sums=0', 'orders / BRL',
 'disjoint selected order sets', 'mixed predicates; missing comparisons', 'Exact predicate before rounding'),
('payment_delta_gt_001', 'order', 'abs(payment_delta) > 0.01; count, sum(delta), sum(abs(delta))',
 'all statuses; status retained', 'no payment event timestamp', 'all snapshot', 'comparable orders',
 'non-comparable predicate=NULL; empty selected set count and sums=0', 'orders / BRL',
 'disjoint selected order sets', 'mixed predicates; missing comparisons', 'Strict >0.01 differs from exact and =0.01'),
('review_score_pair_mean', 'review/order pair', 'sum(review_score)::numeric / nullif(count(review_score),0)',
 'all statuses', 'no date grouping', 'all snapshot', 'pairs with non-NULL score',
 'missing scores excluded; out-of-range scores retained and counted separately', 'score', 'none',
 'all means; seller/item replication', 'Source pair weighting; not causal'),
('review_score_id_mean', 'review_id', 'sum(unambiguous review_score)::numeric / nullif(count(review_score),0)',
 'all statuses', 'no date grouping', 'all snapshot', 'IDs with unambiguous full payload and non-NULL score',
 'conflicting IDs excluded with count; no arbitrary payload chosen', 'score', 'none',
 'all means; association/item replication', 'One vote per unambiguous review ID'),
('review_score_order_mean', 'order', 'sum(order_review_avg) / nullif(count(order_review_avg),0)',
 'all statuses', 'no date grouping', 'all snapshot', 'orders with at least one non-NULL pair score',
 'orders without scores excluded; no score=0 imputation', 'score', 'none', 'all means',
 'One vote per order, after averaging its observed pair scores'),
('is_late_calendar_day', 'order', 'delivered_date::date > estimated_date::date',
 'order_status=delivered', 'source local calendar dates; timezone unknown', 'all snapshot',
 'delivered orders with both dates', 'missing/ineligible=NULL', 'boolean', 'counts on disjoint eligible orders',
 'rates require own eligible denominator', 'Named calendar-day alternative; not buyout or attribution'),
('is_late_timestamp', 'order', 'delivered_date > estimated_date', 'order_status=delivered',
 'source timestamps without timezone', 'all snapshot', 'delivered orders with both timestamps',
 'missing/ineligible=NULL', 'boolean', 'counts on disjoint eligible orders', 'rates require own eligible denominator',
 'Named full-timestamp alternative; no hidden winner'),
('is_handover_after_min_item_deadline', 'order', 'carrier_date > min(shipping_limit_at)',
 'all statuses with observed carrier timestamp', 'source timestamps without timezone', 'all snapshot',
 'nonempty items with all deadlines known and observed carrier timestamp',
 'no/incomplete deadlines or carrier timestamp=NULL', 'boolean', 'counts on disjoint eligible orders',
 'item/seller attribution; rates', 'Order timestamp compared with earliest item deadline; no causal blame'),
('is_handover_after_max_item_deadline', 'order', 'carrier_date > max(shipping_limit_at)',
 'all statuses with observed carrier timestamp', 'source timestamps without timezone', 'all snapshot',
 'nonempty items with all deadlines known and observed carrier timestamp',
 'no/incomplete deadlines or carrier timestamp=NULL', 'boolean', 'counts on disjoint eligible orders',
 'item/seller attribution; rates', 'Order timestamp compared with latest item deadline; no causal blame'),
('purchase_to_delivery_days', 'order', 'extract(epoch from (delivered_date-purchase_timestamp))::numeric/86400',
 'order_status=delivered', 'source timestamps without timezone; fractional elapsed days', 'all snapshot',
 'when averaging: delivered orders with non-NULL, nonnegative purchase-to-delivery interval',
 'missing dates/negative interval=NULL; unrelated carrier anomalies do not exclude', 'days',
 'elapsed durations are not a business total', 'means and rates require eligible components',
 'Observed purchase-to-delivery interval, not a complete lifetime/censoring model'),
('purchase_to_carrier_days', 'order', 'extract(epoch from (carrier_date-purchase_timestamp))::numeric/86400',
 'all statuses with observed dates', 'source timestamps without timezone; fractional elapsed days', 'all snapshot',
 'when averaging: orders with non-NULL, nonnegative purchase-to-carrier interval',
 'missing dates/negative interval=NULL', 'days', 'elapsed durations are not a business total',
 'means and rates require eligible components', 'Order carrier timestamp does not establish item/seller handoff time'),
('carrier_to_delivery_days', 'order', 'extract(epoch from (delivered_date-carrier_date))::numeric/86400',
 'order_status=delivered', 'source timestamps without timezone; fractional elapsed days', 'all snapshot',
 'when averaging: delivered orders with non-NULL, nonnegative carrier-to-delivery interval',
 'missing dates/negative interval=NULL; unrelated purchase anomalies do not exclude', 'days',
 'elapsed durations are not a business total', 'means and rates require eligible components',
 'Observed order-level interval, no causal attribution');

CREATE VIEW mart.v_orders AS
WITH items AS (
    SELECT order_id,
           count(*) AS source_rows_count,
           count(*) AS units_count,
           count(DISTINCT (product_id, seller_id)) AS distinct_product_seller_lines_count,
           count(DISTINCT seller_id) AS sellers_count,
           count(price) AS price_valid_count,
           count(freight_value) AS freight_valid_count,
           count(*) FILTER (WHERE price IS NOT NULL AND freight_value IS NOT NULL)
               AS item_components_valid_count,
           sum(price) AS item_revenue_known_sum,
           sum(freight_value) AS freight_known_sum,
           sum(price + freight_value) AS order_gmv_known_sum,
           CASE WHEN count(price) = count(*) THEN sum(price) END AS item_revenue,
           CASE WHEN count(freight_value) = count(*) THEN sum(freight_value) END AS freight_amount,
           CASE WHEN count(*) FILTER (WHERE price IS NOT NULL AND freight_value IS NOT NULL) = count(*)
                THEN sum(price + freight_value) END AS order_gmv,
           count(shipping_limit_at) AS item_deadline_valid_count,
           min(shipping_limit_at) AS min_item_shipping_limit_at,
           max(shipping_limit_at) AS max_item_shipping_limit_at
    FROM core.fact_order_item
    GROUP BY order_id
), payments AS (
    SELECT order_id,
           count(*) AS payments_count,
           count(payment_value) AS payment_valid_count,
           sum(payment_value) AS payment_known_sum,
           CASE WHEN count(payment_value) = count(*) THEN sum(payment_value) END AS payment_amount
    FROM core.fact_payment
    GROUP BY order_id
), reviews AS (
    SELECT order_id,
           count(*) AS review_pairs_count,
           count(review_score) AS review_score_count,
           count(*) FILTER (WHERE review_score NOT BETWEEN 1 AND 5) AS review_score_out_of_range_count,
           sum(review_score)::numeric AS review_score_sum,
           avg(review_score::numeric) AS review_avg_pair_score
    FROM core.fact_review
    GROUP BY order_id
)
SELECT o.*,
       s.is_revenue,
       o.order_status = 'delivered' AS is_delivered,
       date_trunc('month', o.order_purchase_timestamp)::date AS purchase_month,
       coalesce(i.source_rows_count, 0::bigint) AS source_rows_count,
       coalesce(i.units_count, 0::bigint) AS units_count,
       coalesce(i.distinct_product_seller_lines_count, 0::bigint) AS distinct_product_seller_lines_count,
       coalesce(i.sellers_count, 0::bigint) AS sellers_count,
       coalesce(i.price_valid_count, 0::bigint) AS price_valid_count,
       coalesce(i.freight_valid_count, 0::bigint) AS freight_valid_count,
       coalesce(i.item_components_valid_count, 0::bigint) AS item_components_valid_count,
       i.item_revenue_known_sum, i.freight_known_sum, i.order_gmv_known_sum,
       i.item_revenue, i.freight_amount, i.order_gmv,
       coalesce(p.payments_count, 0::bigint) AS payments_count,
       coalesce(p.payment_valid_count, 0::bigint) AS payment_valid_count,
       p.payment_known_sum, p.payment_amount,
       CASE WHEN i.order_id IS NOT NULL AND p.order_id IS NOT NULL THEN 'both'
            WHEN i.order_id IS NOT NULL THEN 'items_only'
            WHEN p.order_id IS NOT NULL THEN 'payments_only'
            ELSE 'neither' END AS payment_coverage,
       coalesce(r.review_pairs_count, 0::bigint) AS review_pairs_count,
       coalesce(r.review_score_count, 0::bigint) AS review_score_count,
       coalesce(r.review_score_out_of_range_count, 0::bigint) AS review_score_out_of_range_count,
       r.review_score_sum, r.review_avg_pair_score,
       coalesce(i.item_deadline_valid_count, 0::bigint) AS item_deadline_valid_count,
       i.min_item_shipping_limit_at, i.max_item_shipping_limit_at
FROM core.fact_order o
JOIN core.dim_order_status s ON s.order_status = o.order_status
LEFT JOIN items i ON i.order_id = o.order_id
LEFT JOIN payments p ON p.order_id = o.order_id
LEFT JOIN reviews r ON r.order_id = o.order_id;

COMMENT ON VIEW mart.v_orders IS
'One row per core order. Each child aggregated independently. Missing child money stays NULL; counts may be zero.';

CREATE VIEW mart.v_order_items AS
SELECT i.*,
       o.customer_id, o.customer_unique_id, o.order_status,
       o.order_purchase_timestamp, o.order_approved_at,
       o.order_delivered_carrier_date, o.order_delivered_customer_date,
       o.order_estimated_delivery_date, o.customer_city, o.customer_state,
       date_trunc('month', o.order_purchase_timestamp)::date AS purchase_month,
       s.is_revenue, o.order_status = 'delivered' AS is_delivered,
       v.category_key, c.name_pt AS category_name_pt, c.name_en AS category_name_en,
       c.is_unknown AS is_unknown_category, c.is_translated AS is_category_translated,
       seller.seller_city, seller.seller_state
FROM core.fact_order_item i
JOIN core.fact_order o ON o.order_id = i.order_id
JOIN core.dim_order_status s ON s.order_status = o.order_status
JOIN core.dim_category_version v ON v.version_id = i.category_version_id
JOIN core.dim_category c ON c.category_key = v.category_key
JOIN core.dim_seller seller ON seller.seller_id = i.seller_id;

COMMENT ON VIEW mart.v_order_items IS
'One row per (order_id,order_item_id), with only many-to-one joins. No allocated order payments/reviews or repeated order money.';

CREATE VIEW mart.v_order_payment_reconciliation AS
WITH comparison AS (
    SELECT order_id, order_status, is_revenue, is_delivered, payment_coverage,
           source_rows_count, price_valid_count, freight_valid_count,
           item_components_valid_count, payments_count, payment_valid_count,
           item_revenue_known_sum, freight_known_sum, order_gmv_known_sum,
           payment_known_sum, item_revenue, freight_amount, order_gmv, payment_amount,
           order_gmv IS NOT NULL AND payment_amount IS NOT NULL AS is_comparable,
           CASE WHEN order_gmv IS NOT NULL AND payment_amount IS NOT NULL
                THEN payment_amount - order_gmv END AS payment_delta
    FROM mart.v_orders
)
SELECT comparison.*,
       abs(payment_delta) AS absolute_payment_delta,
       payment_delta <> 0 AS delta_nonzero_exact,
       abs(payment_delta) > 0.01::numeric AS delta_gt_001,
       abs(payment_delta) = 0.01::numeric AS delta_eq_001
FROM comparison;

CREATE VIEW mart.v_payment_reconciliation AS
WITH summary AS (
    SELECT order_status, payment_coverage,
           count(*) AS orders_count,
           sum(source_rows_count) AS source_rows_count,
           sum(price_valid_count) AS price_valid_count,
           sum(freight_valid_count) AS freight_valid_count,
           sum(item_components_valid_count) AS item_components_valid_count,
           sum(payments_count) AS payments_count,
           sum(payment_valid_count) AS payment_valid_count,
           count(order_gmv) AS orders_with_known_gmv,
           count(payment_amount) AS orders_with_known_payment_amount,
           count(*) FILTER (WHERE source_rows_count > 0 AND order_gmv IS NULL) AS orders_with_incomplete_gmv,
           count(*) FILTER (WHERE payments_count > 0 AND payment_amount IS NULL) AS orders_with_incomplete_payment,
           sum(order_gmv) AS known_order_gmv_sum,
           sum(payment_amount) AS known_payment_amount_sum,
           count(*) FILTER (WHERE is_comparable) AS comparable_orders,
           count(*) FILTER (WHERE NOT is_comparable) AS non_comparable_orders,
           sum(payment_delta) AS signed_delta_sum,
           sum(absolute_payment_delta) AS absolute_delta_sum,
           count(*) FILTER (WHERE delta_nonzero_exact) AS exact_mismatch_orders,
           coalesce(sum(payment_delta) FILTER (WHERE delta_nonzero_exact), 0::numeric) AS exact_signed_delta_sum,
           coalesce(sum(absolute_payment_delta) FILTER (WHERE delta_nonzero_exact), 0::numeric) AS exact_absolute_delta_sum,
           count(*) FILTER (WHERE delta_gt_001) AS gt_001_mismatch_orders,
           coalesce(sum(payment_delta) FILTER (WHERE delta_gt_001), 0::numeric) AS gt_001_signed_delta_sum,
           coalesce(sum(absolute_payment_delta) FILTER (WHERE delta_gt_001), 0::numeric) AS gt_001_absolute_delta_sum,
           count(*) FILTER (WHERE delta_eq_001) AS eq_001_mismatch_orders,
           coalesce(sum(payment_delta) FILTER (WHERE delta_eq_001), 0::numeric) AS eq_001_signed_delta_sum,
           coalesce(sum(absolute_payment_delta) FILTER (WHERE delta_eq_001), 0::numeric) AS eq_001_absolute_delta_sum
    FROM mart.v_order_payment_reconciliation
    GROUP BY order_status, payment_coverage
)
SELECT s.order_status, s.is_revenue, coverage.payment_coverage,
       coalesce(g.orders_count, 0::bigint) AS orders_count,
       coalesce(g.source_rows_count, 0::numeric) AS source_rows_count,
       coalesce(g.price_valid_count, 0::numeric) AS price_valid_count,
       coalesce(g.freight_valid_count, 0::numeric) AS freight_valid_count,
       coalesce(g.item_components_valid_count, 0::numeric) AS item_components_valid_count,
       coalesce(g.payments_count, 0::numeric) AS payments_count,
       coalesce(g.payment_valid_count, 0::numeric) AS payment_valid_count,
       coalesce(g.orders_with_known_gmv, 0::bigint) AS orders_with_known_gmv,
       coalesce(g.orders_with_known_payment_amount, 0::bigint) AS orders_with_known_payment_amount,
       coalesce(g.orders_with_incomplete_gmv, 0::bigint) AS orders_with_incomplete_gmv,
       coalesce(g.orders_with_incomplete_payment, 0::bigint) AS orders_with_incomplete_payment,
       g.known_order_gmv_sum, g.known_payment_amount_sum,
       coalesce(g.comparable_orders, 0::bigint) AS comparable_orders,
       coalesce(g.non_comparable_orders, 0::bigint) AS non_comparable_orders,
       g.signed_delta_sum, g.absolute_delta_sum,
       coalesce(g.exact_mismatch_orders, 0::bigint) AS exact_mismatch_orders,
       coalesce(g.exact_signed_delta_sum, 0::numeric) AS exact_signed_delta_sum,
       coalesce(g.exact_absolute_delta_sum, 0::numeric) AS exact_absolute_delta_sum,
       coalesce(g.gt_001_mismatch_orders, 0::bigint) AS gt_001_mismatch_orders,
       coalesce(g.gt_001_signed_delta_sum, 0::numeric) AS gt_001_signed_delta_sum,
       coalesce(g.gt_001_absolute_delta_sum, 0::numeric) AS gt_001_absolute_delta_sum,
       coalesce(g.eq_001_mismatch_orders, 0::bigint) AS eq_001_mismatch_orders,
       coalesce(g.eq_001_signed_delta_sum, 0::numeric) AS eq_001_signed_delta_sum,
       coalesce(g.eq_001_absolute_delta_sum, 0::numeric) AS eq_001_absolute_delta_sum
FROM core.dim_order_status s
CROSS JOIN (VALUES ('both'), ('items_only'), ('payments_only'), ('neither')) AS coverage(payment_coverage)
LEFT JOIN summary g ON g.order_status = s.order_status AND g.payment_coverage = coverage.payment_coverage;

COMMENT ON VIEW mart.v_payment_reconciliation IS
'Status x all four child-presence classes, including empty classes. Exact, abs(delta)>0.01 and abs(delta)=0.01 use separate matching counts/net/absolute sums.';

CREATE VIEW mart.v_review_payload_variants AS
SELECT review_id, review_score, review_comment_title, review_comment_message,
       review_creation_date, review_answer_timestamp,
       count(*) AS variant_association_count
FROM core.fact_review
GROUP BY review_id, review_score, review_comment_title, review_comment_message,
         review_creation_date, review_answer_timestamp;

CREATE VIEW mart.v_review AS
WITH variants AS (
    SELECT review_id, count(*) AS payload_variant_count,
           sum(variant_association_count) AS association_count
    FROM mart.v_review_payload_variants
    GROUP BY review_id
)
SELECT v.review_id, v.payload_variant_count, v.association_count,
       v.payload_variant_count > 1 AS has_payload_conflict,
       p.review_score, p.review_comment_title, p.review_comment_message,
       p.review_creation_date, p.review_answer_timestamp
FROM variants v
LEFT JOIN mart.v_review_payload_variants p
       ON p.review_id = v.review_id AND v.payload_variant_count = 1;

COMMENT ON VIEW mart.v_review IS
'One row per review_id. Payload is NULL on conflict; all distinct variants and original pairs stay accessible. No arbitrary representative.';

CREATE VIEW mart.v_review_weighting AS
SELECT 'review_order_pair'::text AS weight_basis,
       count(*) AS population_units,
       count(review_score) AS denominator,
       sum(review_score)::numeric AS numerator,
       avg(review_score::numeric) AS mean_score,
       count(*) FILTER (WHERE review_score IS NULL) AS excluded_units,
       count(*) FILTER (WHERE review_score NOT BETWEEN 1 AND 5) AS out_of_range_score_units
FROM core.fact_review
UNION ALL
SELECT 'review_id_unambiguous_payload', count(*), count(review_score),
       sum(review_score)::numeric, avg(review_score::numeric),
       count(*) FILTER (WHERE has_payload_conflict OR review_score IS NULL),
       count(*) FILTER (WHERE review_score NOT BETWEEN 1 AND 5)
FROM mart.v_review
UNION ALL
SELECT 'order_mean_of_review_pairs', count(*), count(review_avg_pair_score),
       sum(review_avg_pair_score), avg(review_avg_pair_score),
       count(*) FILTER (WHERE review_avg_pair_score IS NULL),
       count(*) FILTER (WHERE review_score_out_of_range_count > 0)
FROM mart.v_orders;

CREATE VIEW mart.v_order_delivery_variants AS
SELECT order_id, order_status, is_delivered,
       order_purchase_timestamp, order_approved_at,
       order_delivered_carrier_date, order_delivered_customer_date,
       order_estimated_delivery_date, source_rows_count, item_deadline_valid_count,
       min_item_shipping_limit_at, max_item_shipping_limit_at,
       CASE WHEN is_delivered AND order_delivered_customer_date IS NOT NULL
                 AND order_estimated_delivery_date IS NOT NULL
            THEN order_delivered_customer_date::date > order_estimated_delivery_date::date
            END AS is_late_calendar_day,
       CASE WHEN is_delivered AND order_delivered_customer_date IS NOT NULL
                 AND order_estimated_delivery_date IS NOT NULL
            THEN order_delivered_customer_date > order_estimated_delivery_date
            END AS is_late_timestamp,
       CASE WHEN order_delivered_carrier_date IS NOT NULL AND source_rows_count > 0
                 AND item_deadline_valid_count = source_rows_count
            THEN order_delivered_carrier_date > min_item_shipping_limit_at
            END AS is_handover_after_min_item_deadline,
       CASE WHEN order_delivered_carrier_date IS NOT NULL AND source_rows_count > 0
                 AND item_deadline_valid_count = source_rows_count
            THEN order_delivered_carrier_date > max_item_shipping_limit_at
            END AS is_handover_after_max_item_deadline,
       CASE WHEN is_delivered AND order_delivered_customer_date >= order_purchase_timestamp
            THEN extract(epoch FROM (order_delivered_customer_date - order_purchase_timestamp))::numeric / 86400
            END AS purchase_to_delivery_days,
       CASE WHEN order_delivered_carrier_date >= order_purchase_timestamp
            THEN extract(epoch FROM (order_delivered_carrier_date - order_purchase_timestamp))::numeric / 86400
            END AS purchase_to_carrier_days,
       CASE WHEN is_delivered AND order_delivered_customer_date >= order_delivered_carrier_date
            THEN extract(epoch FROM (order_delivered_customer_date - order_delivered_carrier_date))::numeric / 86400
            END AS carrier_to_delivery_days
FROM mart.v_orders;
