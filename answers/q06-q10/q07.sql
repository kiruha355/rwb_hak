-- Q7: threshold applied to orders in each population, not just measured orders.
-- Change min_orders here for sensitivity; 500 is the organizer's threshold.
WITH params AS (SELECT 500::bigint AS min_orders),
populations AS (
    SELECT 'all_statuses'::text AS population, o.customer_state, d.*
    FROM mart.v_orders o JOIN mart.v_order_delivery_variants d USING (order_id)
    UNION ALL
    SELECT 'delivered', o.customer_state, d.*
    FROM mart.v_orders o JOIN mart.v_order_delivery_variants d USING (order_id)
    WHERE d.is_delivered
), alternatives AS (
    SELECT p.*, 'calendar_day'::text AS late_basis, is_late_calendar_day AS is_late FROM populations p
    UNION ALL
    SELECT p.*, 'timestamp', is_late_timestamp FROM populations p
)
SELECT population, customer_state, late_basis, count(*) AS orders_count,
       count(purchase_to_delivery_days) AS duration_denominator,
       avg(purchase_to_delivery_days) AS avg_delivery_days,
       count(is_late) AS late_denominator,
       count(*) FILTER (WHERE is_late) AS late_orders,
       100.0 * count(*) FILTER (WHERE is_late) / nullif(count(is_late), 0) AS late_pct
FROM alternatives GROUP BY population, customer_state, late_basis
HAVING count(*) >= (SELECT min_orders FROM params)
ORDER BY population, customer_state NULLS LAST, late_basis;
