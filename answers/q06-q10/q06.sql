-- Q6: purchase calendar date; all statuses and delivered are alternatives.
-- Return every product tied for the maximum number of distinct non-NULL prices.
WITH populations AS (
    SELECT 'all_statuses'::text AS population, i.* FROM mart.v_order_items i
    UNION ALL
    SELECT 'delivered', i.* FROM mart.v_order_items i WHERE i.is_delivered
), counts AS (
    SELECT population, product_id, count(DISTINCT price) AS distinct_prices,
           count(*) FILTER (WHERE price IS NULL) AS units_with_unknown_price
    FROM populations GROUP BY population, product_id
), winners AS (
    SELECT *, max(distinct_prices) OVER (PARTITION BY population) AS max_distinct_prices
    FROM counts
)
SELECT p.population, p.product_id, w.distinct_prices, w.units_with_unknown_price,
       p.order_purchase_timestamp::date AS purchase_date, p.price, count(*) AS units_sold
FROM populations p JOIN winners w USING (population, product_id)
WHERE w.distinct_prices = w.max_distinct_prices AND w.distinct_prices > 0
GROUP BY p.population, p.product_id, w.distinct_prices, w.units_with_unknown_price,
         p.order_purchase_timestamp::date, p.price
ORDER BY p.population, p.product_id, purchase_date NULLS LAST, p.price NULLS LAST;
