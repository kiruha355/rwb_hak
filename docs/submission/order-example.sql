-- Prepared read-only illustration for the checkpoint. NOT executed by W-12.
-- Run only after a verified core/mart build on the approved PostgreSQL endpoint.
-- A linked CSV example with the same ID is in order-example.json.
WITH item_totals AS (
    SELECT order_id, count(*) AS item_rows,
           sum(price) AS item_price, sum(freight_value) AS freight,
           CASE WHEN count(price) = count(*) AND count(freight_value) = count(*)
                THEN sum(price + freight_value) END AS order_gmv
    FROM core.fact_order_item
    WHERE order_id = 'e481f51cbdc54678b7cc49136f2d6af7'
    GROUP BY order_id
), payment_totals AS (
    SELECT order_id, count(*) AS payment_rows,
           CASE WHEN count(payment_value) = count(*) THEN sum(payment_value) END AS payment_amount
    FROM core.fact_payment
    WHERE order_id = 'e481f51cbdc54678b7cc49136f2d6af7'
    GROUP BY order_id
), review_totals AS (
    SELECT order_id, count(*) AS review_pairs
    FROM core.fact_review
    WHERE order_id = 'e481f51cbdc54678b7cc49136f2d6af7'
    GROUP BY order_id
)
SELECT o.order_id, o.customer_id, o.customer_unique_id, o.order_status,
       o.customer_zip_code_prefix, o.customer_zip_code_prefix_validated,
       i.item_rows, p.payment_rows, r.review_pairs,
       i.item_price, i.freight, i.order_gmv, p.payment_amount,
       p.payment_amount - i.order_gmv AS payment_delta
FROM core.fact_order o
LEFT JOIN item_totals i USING (order_id)
LEFT JOIN payment_totals p USING (order_id)
LEFT JOIN review_totals r USING (order_id)
WHERE o.order_id = 'e481f51cbdc54678b7cc49136f2d6af7';
