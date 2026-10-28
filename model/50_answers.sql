-- W-10. Answer relations contain calculations, never baseline answer rows.
-- Read only core/mart. Regression values belong in answers/control.sql.

CREATE VIEW mart.q01_revenue_monthly AS
WITH calendar AS (
    SELECT DISTINCT month_start
    FROM core.dim_date
    WHERE month_start >= DATE '2016-09-01'
      AND month_start < DATE '2018-09-01'
), monthly AS (
    SELECT purchase_month AS month_start,
           count(*) AS orders_placed,
           count(*) FILTER (WHERE is_delivered) AS orders_delivered,
           count(*) FILTER (WHERE is_revenue) AS orders_revenue_eligible,
           count(*) FILTER (WHERE is_revenue AND source_rows_count = 0) AS revenue_orders_without_items,
           coalesce(sum(source_rows_count) FILTER (WHERE is_revenue), 0::numeric) AS revenue_item_rows_count,
           coalesce(sum(price_valid_count) FILTER (WHERE is_revenue), 0::numeric) AS revenue_price_valid_count,
           coalesce(sum(source_rows_count - price_valid_count) FILTER (WHERE is_revenue), 0::numeric)
               AS revenue_price_missing_count,
           coalesce(sum(item_revenue_known_sum) FILTER (WHERE is_revenue), 0::numeric) AS item_revenue_known_sum,
           CASE WHEN count(*) FILTER (WHERE is_revenue AND
                                (source_rows_count = 0 OR price_valid_count <> source_rows_count)) = 0
                THEN coalesce(sum(item_revenue) FILTER (WHERE is_revenue), 0::numeric)
                END AS item_revenue
    FROM mart.v_orders
    WHERE order_purchase_timestamp >= TIMESTAMP '2016-09-01 00:00:00'
      AND order_purchase_timestamp < TIMESTAMP '2018-09-01 00:00:00'
    GROUP BY purchase_month
)
SELECT c.month_start,
       coalesce(m.orders_placed, 0::bigint) AS orders_placed,
       coalesce(m.orders_delivered, 0::bigint) AS orders_delivered,
       coalesce(m.orders_revenue_eligible, 0::bigint) AS orders_revenue_eligible,
       coalesce(m.revenue_orders_without_items, 0::bigint) AS revenue_orders_without_items,
       coalesce(m.revenue_item_rows_count, 0::numeric) AS revenue_item_rows_count,
       coalesce(m.revenue_price_valid_count, 0::numeric) AS revenue_price_valid_count,
       coalesce(m.revenue_price_missing_count, 0::numeric) AS revenue_price_missing_count,
       CASE WHEN m.month_start IS NULL THEN 0::numeric ELSE m.item_revenue END AS item_revenue,
       coalesce(m.item_revenue_known_sum, 0::numeric) AS item_revenue_known_sum
FROM calendar c
LEFT JOIN monthly m ON m.month_start = c.month_start;

COMMENT ON VIEW mart.q01_revenue_monthly IS
'Q1: 24 calendar purchase months [Sep2016,Sep2018); placed and delivered counts separate; revenue excludes freight. Unknown prices are not zero.';

CREATE VIEW mart.q02_sellers_top10 AS
WITH sellers AS (
    SELECT seller_id, seller_city, seller_state,
           count(DISTINCT order_id) FILTER (WHERE is_delivered) AS orders_delivered,
           count(*) FILTER (WHERE is_delivered) AS units_delivered,
           count(DISTINCT order_id) AS orders_all_statuses,
           count(*) AS units_all_statuses,
           count(DISTINCT order_id) FILTER (WHERE is_revenue) AS orders_revenue_eligible,
           count(*) FILTER (WHERE is_revenue) AS revenue_item_rows_count,
           count(price) FILTER (WHERE is_revenue) AS revenue_price_valid_count,
           count(*) FILTER (WHERE is_revenue AND price IS NULL) AS revenue_price_missing_count,
           sum(price) FILTER (WHERE is_revenue) AS item_revenue_known_sum,
           CASE WHEN count(*) FILTER (WHERE is_revenue AND price IS NULL) = 0
                THEN coalesce(sum(price) FILTER (WHERE is_revenue), 0::numeric)
                END AS item_revenue
    FROM mart.v_order_items
    GROUP BY seller_id, seller_city, seller_state
)
SELECT seller_id, seller_city, seller_state,
       orders_delivered, units_delivered, orders_all_statuses, units_all_statuses,
       orders_revenue_eligible, revenue_item_rows_count,
       revenue_price_valid_count, revenue_price_missing_count,
       item_revenue, item_revenue_known_sum
FROM sellers
ORDER BY item_revenue DESC NULLS LAST, seller_id
LIMIT 10;

COMMENT ON VIEW mart.q02_sellers_top10 IS
'Q2: all-snapshot seller ranking by own eligible item price, no freight. Delivered order/unit counts and all-status counts are separate. City/state retain source text.';

CREATE VIEW mart.q03_average_order AS
SELECT count(*) AS n_delivered_orders,
       count(order_gmv) AS n_order_gmv,
       count(*) FILTER (WHERE order_gmv IS NULL) AS n_excluded_order_gmv,
       sum(order_gmv) AS order_gmv_sum,
       avg(order_gmv) AS avg_order_gmv,
       round(avg(order_gmv), 2) AS avg_order_gmv_rounded,
       count(payment_amount) AS n_payment_amount,
       count(*) FILTER (WHERE payment_amount IS NULL) AS n_excluded_payment_amount,
       sum(payment_amount) AS payment_amount_sum,
       avg(payment_amount) AS avg_payment_amount,
       round(avg(payment_amount), 2) AS avg_payment_amount_rounded,
       coalesce(sum(source_rows_count), 0::numeric) AS source_rows_count,
       coalesce(sum(units_count), 0::numeric) AS units_count,
       coalesce(sum(distinct_product_seller_lines_count), 0::numeric) AS distinct_product_seller_lines_count,
       sum(source_rows_count)::numeric / nullif(count(*), 0) AS avg_source_rows,
       sum(units_count)::numeric / nullif(count(*), 0) AS avg_units,
       sum(distinct_product_seller_lines_count)::numeric / nullif(count(*), 0)
           AS avg_distinct_product_seller_lines
FROM mart.v_orders
WHERE is_delivered;

COMMENT ON VIEW mart.q03_average_order IS
'Q3: order average of item price plus freight. Payments have their own denominator. Source rows/units differ from distinct product-seller lines. Exact numeric plus presentation rounding.';

CREATE VIEW mart.q04_buyers_repeat AS
WITH buyer_orders AS (
    SELECT customer_unique_id, count(*) AS orders_count,
           count(*) FILTER (WHERE order_purchase_timestamp IS NULL) AS unknown_purchase_timestamp_orders
    FROM core.fact_order
    GROUP BY customer_unique_id
)
SELECT 'all_snapshot'::text AS observation_window,
       count(*) AS buyers,
       count(*) FILTER (WHERE orders_count > 1) AS repeat_buyers,
       count(*) FILTER (WHERE orders_count > 1)::numeric / nullif(count(*), 0) AS repeat_buyer_ratio,
       100::numeric * count(*) FILTER (WHERE orders_count > 1) / nullif(count(*), 0) AS repeat_buyer_pct,
       round(100::numeric * count(*) FILTER (WHERE orders_count > 1) / nullif(count(*), 0), 2)
           AS repeat_buyer_pct_rounded,
       coalesce(sum(orders_count), 0::numeric) AS orders_count,
       coalesce(sum(unknown_purchase_timestamp_orders), 0::numeric) AS unknown_purchase_timestamp_orders
FROM buyer_orders;

CREATE VIEW mart.q04_buyers_repeat_q1_window AS
WITH buyer_orders AS (
    SELECT customer_unique_id, count(*) AS orders_count
    FROM core.fact_order
    WHERE order_purchase_timestamp >= TIMESTAMP '2016-09-01 00:00:00'
      AND order_purchase_timestamp < TIMESTAMP '2018-09-01 00:00:00'
    GROUP BY customer_unique_id
)
SELECT '[2016-09-01,2018-09-01)'::text AS observation_window,
       count(*) AS buyers,
       count(*) FILTER (WHERE orders_count > 1) AS repeat_buyers,
       count(*) FILTER (WHERE orders_count > 1)::numeric / nullif(count(*), 0) AS repeat_buyer_ratio,
       100::numeric * count(*) FILTER (WHERE orders_count > 1) / nullif(count(*), 0) AS repeat_buyer_pct,
       round(100::numeric * count(*) FILTER (WHERE orders_count > 1) / nullif(count(*), 0), 2)
           AS repeat_buyer_pct_rounded,
       coalesce(sum(orders_count), 0::numeric) AS orders_count
FROM buyer_orders;

COMMENT ON VIEW mart.q04_buyers_repeat IS
'Q4 default: all statuses, all observed snapshot, customer_unique_id; absolute repeat buyers and ratio/pct. Not lifetime or retention.';
COMMENT ON VIEW mart.q04_buyers_repeat_q1_window IS
'Q4 named alternative: buyer grouping and >1 criterion after purchase-window filter; not a hidden global cutoff.';

CREATE VIEW mart.q05_category_revenue AS
WITH category_items AS (
    SELECT category_key,
           count(*) AS revenue_item_rows_count,
           count(price) AS revenue_price_valid_count,
           count(*) FILTER (WHERE price IS NULL) AS revenue_price_missing_count,
           sum(price) AS item_revenue_known_sum,
           CASE WHEN count(price) = count(*) THEN sum(price) END AS item_revenue
    FROM mart.v_order_items
    WHERE is_revenue
    GROUP BY category_key
), categories AS (
    SELECT c.category_key, c.name_pt, c.name_en, c.is_unknown, c.is_translated,
           coalesce(i.revenue_item_rows_count, 0::bigint) AS revenue_item_rows_count,
           coalesce(i.revenue_price_valid_count, 0::bigint) AS revenue_price_valid_count,
           coalesce(i.revenue_price_missing_count, 0::bigint) AS revenue_price_missing_count,
           CASE WHEN i.category_key IS NULL THEN 0::numeric ELSE i.item_revenue END AS item_revenue,
           CASE WHEN i.category_key IS NULL THEN 0::numeric ELSE i.item_revenue_known_sum END AS item_revenue_known_sum
    FROM core.dim_category c
    LEFT JOIN category_items i ON i.category_key = c.category_key
), totals AS (
    SELECT categories.*,
           CASE WHEN bool_and(item_revenue IS NOT NULL) OVER ()
                THEN sum(item_revenue) OVER () END AS total_item_revenue,
           sum(revenue_item_rows_count) OVER () AS total_revenue_item_rows_count,
           sum(revenue_price_valid_count) OVER () AS total_revenue_price_valid_count
    FROM categories
)
SELECT totals.*,
       100::numeric * item_revenue / nullif(total_item_revenue, 0) AS revenue_pct,
       round(100::numeric * item_revenue / nullif(total_item_revenue, 0), 2) AS revenue_pct_rounded
FROM totals;

COMMENT ON VIEW mart.q05_category_revenue IS
'Q5: all category members including unknown and untranslated known PT names; price-only eligible item revenue and same-population denominator. Shares rounded only for display.';

-- Q6-Q10 deliberately absent: source tasks.md has not published their wording.
-- Adding fabricated zero/empty answers would misrepresent unknown requirements.
