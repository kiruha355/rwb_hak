-- All four presence classes per status, exact and >0.01 comparators separate.
SELECT * FROM mart.v_payment_reconciliation ORDER BY order_status, payment_coverage;
