-- Q2: own seller item revenue, delivered counts; all-status counts separate.
SELECT * FROM mart.q02_sellers_top10 ORDER BY item_revenue DESC NULLS LAST, seller_id;
