-- Q8: snapshot statuses, not transitions; denominator includes every order.
WITH counts AS (
    SELECT order_status, count(*) AS orders_count,
           count(*) FILTER (WHERE source_rows_count = 0) AS orders_without_items
    FROM mart.v_orders GROUP BY order_status
)
SELECT order_status, orders_count,
       100.0 * orders_count / nullif(sum(orders_count) OVER (), 0) AS orders_pct,
       orders_without_items
FROM counts ORDER BY orders_count DESC, order_status;
