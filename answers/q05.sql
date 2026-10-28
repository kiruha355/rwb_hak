-- Q5: retain unknown and untranslated categories; common exact denominator.
SELECT * FROM mart.q05_category_revenue ORDER BY item_revenue DESC NULLS LAST, category_key;
