-- Dashboard export: one JSON document from core/mart, read-only.
-- Run: make dashboard (writes dashboard/data.js). Never reads raw.
--
-- Layout is columnar to keep the file small: every array in `orders` has one
-- element per order, every array in `items` one element per order item, and
-- items.o points into the orders arrays. Order ids are one concatenated string
-- (32 chars each). Small indexes are one base-36 char per order and flags are
-- '1'/'0', with '.' for NULL (unknown is never folded into false). Money is in integer cents (source
-- scale <= 2 is enforced by 30_quality/90_checks), NULL stays null.
-- Dates are whole days since 2016-01-01; they are only shown in drill-through.
-- The UI recomputes every metric from these rows; the mart answer views are
-- exported alongside so the page can show the UI-vs-SQL reconciliation.
\set ON_ERROR_STOP on
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY;
\set b36 '0123456789abcdefghijklmnopqrstuvwxyz'

WITH months AS (
    SELECT DISTINCT month_start
    FROM core.dim_date
    WHERE month_start >= (SELECT date_trunc('month', min(order_purchase_timestamp)) FROM core.fact_order)
      AND month_start <= (SELECT date_trunc('month', max(order_purchase_timestamp)) FROM core.fact_order)
), month_idx AS (
    SELECT month_start, (row_number() OVER (ORDER BY month_start) - 1)::int AS i FROM months
), states AS (
    SELECT customer_state, (row_number() OVER (ORDER BY customer_state) - 1)::int AS i
    FROM (SELECT DISTINCT customer_state FROM core.fact_order WHERE customer_state IS NOT NULL) s
), statuses AS (
    SELECT order_status, is_revenue, (row_number() OVER (ORDER BY order_status) - 1)::int AS i
    FROM core.dim_order_status
), coverages AS (
    SELECT c, (ord - 1)::int AS i
    FROM unnest(ARRAY['both', 'items_only', 'payments_only', 'neither']) WITH ORDINALITY AS t(c, ord)
), categories AS (
    SELECT category_key, name_pt, name_en, is_unknown, is_translated,
           (row_number() OVER (ORDER BY category_key) - 1)::int AS i
    FROM core.dim_category
), sellers AS (
    SELECT seller_id, seller_city, seller_state,
           (row_number() OVER (ORDER BY seller_id) - 1)::int AS i
    FROM core.dim_seller
), buyers AS (
    SELECT customer_unique_id, (row_number() OVER (ORDER BY customer_unique_id) - 1)::int AS i
    FROM core.dim_customer
), o AS (
    SELECT (row_number() OVER (ORDER BY v.order_id) - 1)::int AS i,
           v.order_id, mi.i AS m, st.i AS state, ss.i AS status, b.i AS buyer,
           cv.i AS cov,
           (v.order_gmv * 100)::bigint AS gmv,
           (v.payment_amount * 100)::bigint AS pay,
           d.is_late_calendar_day AS late_day,
           d.is_late_timestamp AS late_ts,
           round(d.purchase_to_delivery_days, 2) AS days,
           d.is_handover_after_min_item_deadline AS ho_min,
           d.is_handover_after_max_item_deadline AS ho_max,
           v.review_score_sum AS rs,
           v.review_score_count AS rn,
           v.order_purchase_timestamp::date - DATE '2016-01-01' AS dp,
           v.order_estimated_delivery_date::date - DATE '2016-01-01' AS de,
           v.order_delivered_customer_date::date - DATE '2016-01-01' AS dd
    FROM mart.v_orders v
    JOIN mart.v_order_delivery_variants d ON d.order_id = v.order_id
    LEFT JOIN month_idx mi ON mi.month_start = v.purchase_month
    LEFT JOIN states st ON st.customer_state = v.customer_state
    JOIN statuses ss ON ss.order_status = v.order_status
    JOIN buyers b ON b.customer_unique_id = v.customer_unique_id
    JOIN coverages cv ON cv.c = v.payment_coverage
), it AS (
    SELECT o.i AS o, c.i AS cat, s.i AS seller,
           (vi.price * 100)::bigint AS price,
           (vi.freight_value * 100)::bigint AS freight
    FROM mart.v_order_items vi
    JOIN o ON o.order_id = vi.order_id
    JOIN categories c ON c.category_key = vi.category_key
    JOIN sellers s ON s.seller_id = vi.seller_id
)
SELECT 'window.CAPIBARA_DATA = ' || json_build_object(
    'meta', json_build_object(
        'exported_at', to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
        'database', current_database(),
        'sources', json_build_array('mart.v_orders', 'mart.v_order_delivery_variants',
                                    'mart.v_order_items', 'mart.v_payment_reconciliation',
                                    'mart.metric_definitions', 'mart.q01..q05', 'core.data_issues')),
    'dicts', json_build_object(
        'months', (SELECT json_agg(to_char(month_start, 'YYYY-MM') ORDER BY i) FROM month_idx),
        'states', (SELECT json_agg(customer_state ORDER BY i) FROM states),
        'statuses', (SELECT json_agg(json_build_object('name', order_status, 'is_revenue', is_revenue) ORDER BY i) FROM statuses),
        'coverages', (SELECT json_agg(c ORDER BY i) FROM coverages),
        'categories', (SELECT json_agg(json_build_array(category_key, name_pt, name_en, is_unknown, is_translated) ORDER BY i) FROM categories),
        'sellers', (SELECT json_agg(json_build_array(seller_id, seller_city, seller_state) ORDER BY i) FROM sellers),
        'buyers_total', (SELECT count(*) FROM buyers)),
    'orders', (SELECT json_build_object(
        'n', count(*),
        'id', string_agg(order_id, '' ORDER BY i),
        'm', string_agg(coalesce(substr(:'b36', m + 1, 1), '.'), '' ORDER BY i),
        'state', string_agg(coalesce(substr(:'b36', state + 1, 1), '.'), '' ORDER BY i),
        'status', string_agg(substr(:'b36', status + 1, 1), '' ORDER BY i),
        'cov', string_agg(substr(:'b36', cov + 1, 1), '' ORDER BY i),
        'late_day', string_agg(CASE late_day WHEN true THEN '1' WHEN false THEN '0' ELSE '.' END, '' ORDER BY i),
        'late_ts', string_agg(CASE late_ts WHEN true THEN '1' WHEN false THEN '0' ELSE '.' END, '' ORDER BY i),
        'ho_min', string_agg(CASE ho_min WHEN true THEN '1' WHEN false THEN '0' ELSE '.' END, '' ORDER BY i),
        'ho_max', string_agg(CASE ho_max WHEN true THEN '1' WHEN false THEN '0' ELSE '.' END, '' ORDER BY i),
        'buyer', json_agg(buyer ORDER BY i),
        'gmv', json_agg(gmv ORDER BY i), 'pay', json_agg(pay ORDER BY i),
        'days', json_agg(days ORDER BY i),
        'rs', json_agg(rs ORDER BY i), 'rn', json_agg(rn ORDER BY i),
        'dp', json_agg(dp ORDER BY i), 'de', json_agg(de ORDER BY i), 'dd', json_agg(dd ORDER BY i))
        FROM o),
    'items', (SELECT json_build_object(
        'o', json_agg(o ORDER BY o, seller, cat, price, freight),
        'cat', json_agg(cat ORDER BY o, seller, cat, price, freight),
        'seller', json_agg(seller ORDER BY o, seller, cat, price, freight),
        'price', json_agg(price ORDER BY o, seller, cat, price, freight),
        'freight', json_agg(freight ORDER BY o, seller, cat, price, freight))
        FROM it),
    'payment_reconciliation', (SELECT json_agg(r ORDER BY r.order_status, r.payment_coverage)
        FROM mart.v_payment_reconciliation r WHERE r.orders_count > 0),
    'data_issues', (SELECT json_agg(json_build_object('code', issue_code, 'entity', entity_type, 'n', n) ORDER BY n DESC, issue_code)
        FROM (SELECT issue_code, entity_type, count(*) AS n FROM core.data_issues GROUP BY 1, 2) x),
    'metric_definitions', (SELECT json_agg(d ORDER BY d.name) FROM mart.metric_definitions d),
    'sql', json_build_object(
        'q01', (SELECT json_agg(q ORDER BY q.month_start) FROM mart.q01_revenue_monthly q),
        'q02', (SELECT json_agg(q) FROM mart.q02_sellers_top10 q),
        'q03', (SELECT row_to_json(q) FROM mart.q03_average_order q),
        'q04', (SELECT row_to_json(q) FROM mart.q04_buyers_repeat q),
        'q05', (SELECT json_agg(q ORDER BY q.item_revenue DESC NULLS LAST) FROM mart.q05_category_revenue q),
        'delivery_days', (SELECT json_build_object(
            'n', count(purchase_to_delivery_days),
            'p50', percentile_cont(0.5) WITHIN GROUP (ORDER BY purchase_to_delivery_days),
            'p90', percentile_cont(0.9) WITHIN GROUP (ORDER BY purchase_to_delivery_days),
            'late_day', count(*) FILTER (WHERE is_late_calendar_day),
            'late_day_eligible', count(is_late_calendar_day))
            FROM mart.v_order_delivery_variants))
)::text || ';';
