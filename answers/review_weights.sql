-- Explicit pair/ID/order weighting; no single default review weight is approved.
SELECT * FROM mart.v_review_weighting ORDER BY weight_basis;
