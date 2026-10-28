-- This file is executed ONLY after raw/core/mart have been rebound to unique
-- w11_* schemas by scripts/verify-model.py. It never targets live raw.
INSERT INTO raw.orders(order_id,customer_id,order_status,order_purchase_timestamp,
 order_approved_at,order_delivered_carrier_date,order_delivered_customer_date,order_estimated_delivery_date)
SELECT id,'c-'||id,'delivered','2017-01-01 10:00:00','2017-01-01 11:00:00',
 '2017-01-02 10:00:00',CASE WHEN id='late-null' THEN NULL ELSE '2017-01-03 18:00:00' END,
 '2017-01-03 00:00:00'
FROM (VALUES ('fanout'),('neither'),('all-null'),('known-zero'),('partial'),
 ('items-only'),('payments-only'),('comp-a'),('comp-b'),('late-null')) x(id);
INSERT INTO raw.customers(customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state)
SELECT customer_id,CASE WHEN order_id IN ('fanout','known-zero') THEN 'same-buyer' ELSE 'b-'||order_id END,
 '1234','source city','SP' FROM raw.orders;
INSERT INTO raw.customers(customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state)
VALUES('unused-context','unused-buyer',NULL,NULL,NULL);
INSERT INTO raw.sellers(seller_id,seller_zip_code_prefix,seller_city,seller_state)
VALUES('s1','1234','sp / sp','SP');
INSERT INTO raw.products(product_id,product_category_name,product_weight_g)
VALUES('p1','cat','10'),('p-unknown',NULL,NULL),('p-untranslated','pc_gamer','0');
INSERT INTO raw.product_category_translation(product_category_name,product_category_name_english)
VALUES('cat','category'),('unused','unused category');
INSERT INTO raw.order_items(order_id,order_item_id,product_id,seller_id,price,freight_value,shipping_limit_date)
VALUES
 ('fanout','1','p1','s1','10','1','2017-01-02 00:00:00'),
 ('fanout','2','p-untranslated','s1','20','2','2017-01-02 12:00:00'),
 ('all-null','1','p-unknown','s1',NULL,NULL,NULL),
 ('known-zero','1','p1','s1','0','0',NULL),
 ('partial','1','p1','s1','5',NULL,NULL),
 ('partial','2','p1','s1','7','1',NULL),
 ('items-only','1','p1','s1','4','1',NULL),
 ('comp-a','1','p1','s1','20','0',NULL),
 ('comp-b','1','p1','s1','30','0',NULL);
INSERT INTO raw.order_payments(order_id,payment_sequential,payment_type,payment_installments,payment_value)
VALUES('fanout','1','credit_card','1','10'),('fanout','2','voucher','1','10'),
 ('fanout','3','boleto','1','10'),('all-null','1','credit_card','0',NULL),
 ('known-zero','1','voucher','1','0'),('partial','1','boleto','1','13'),
 ('payments-only','1','boleto','1','9'),('comp-a','1','boleto','1','20'),
 ('comp-b','1','boleto','1','30');
INSERT INTO raw.order_reviews(review_id,order_id,review_score,review_comment_title,review_comment_message,
 review_creation_date,review_answer_timestamp)
VALUES('shared-review','fanout','5',NULL,'retained text','2017-01-04 00:00:00','2017-01-05 12:00:00'),
 ('second-review','fanout','1','','line one
line two','2017-01-04 00:00:00',NULL),
 ('shared-review','known-zero','5',NULL,'retained text','2017-01-04 00:00:00','2017-01-05 12:00:00'),
 ('null-score','all-null',NULL,NULL,NULL,NULL,NULL);
