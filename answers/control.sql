-- Pinned regression oracle, never included in model/build.sql.
-- Before passing the variable, independently establish that the LIVE raw/core
-- input matches the eight CSV contents in answers/baseline-manifest.json.
-- Merely hashing the JSON or matching a total does not establish that binding.
-- No unverified manifest should be supplied as if that check had passed.
-- psql -X -v ON_ERROR_STOP=1 -v verified_input_manifest_sha256=<verified hash> -f answers/control.sql
\set ON_ERROR_STOP on
\if :{?verified_input_manifest_sha256}
\else
DO $w10_blocked$ BEGIN
    RAISE EXCEPTION 'BLOCKED: verified_input_manifest_sha256 missing; live raw/core-to-input binding not established';
END $w10_blocked$;
\endif

SELECT :'verified_input_manifest_sha256' =
       '8afb8691d866ef5f5ed465eb9111df521408e1b3d84408d5f0c03337477312c3'
       AS w10_baseline_manifest_matches
\gset
\if :w10_baseline_manifest_matches
\else
DO $w10_blocked$ BEGIN
    RAISE EXCEPTION 'BLOCKED: input manifest differs from pinned CSV reference; choose a matching oracle explicitly';
END $w10_blocked$;
\endif

CREATE TEMP VIEW w10_control_results AS
WITH checks(metric_name, expected, actual) AS (
    SELECT 'q01.months', 24::numeric, count(*)::numeric FROM mart.q01_revenue_monthly
    UNION ALL
    SELECT 'q01.orders_placed', 99421, sum(orders_placed) FROM mart.q01_revenue_monthly
    UNION ALL
    SELECT 'q01.orders_delivered', 96478, sum(orders_delivered) FROM mart.q01_revenue_monthly
    UNION ALL
    SELECT 'q01.item_revenue', 13221498.11, sum(item_revenue) FROM mart.q01_revenue_monthly
    UNION ALL
    SELECT 'q01.unknown_revenue_months', 0, count(*) FROM mart.q01_revenue_monthly WHERE item_revenue IS NULL
    UNION ALL
    SELECT 'q01.empty_nov2016_orders', 0, orders_placed FROM mart.q01_revenue_monthly WHERE month_start=DATE '2016-11-01'
    UNION ALL
    SELECT 'q02.sellers_returned', 10, count(*) FROM mart.q02_sellers_top10
    UNION ALL
    SELECT 'q02.top_revenue', 226987.93, item_revenue FROM mart.q02_sellers_top10
        WHERE seller_id=(SELECT seller_id FROM mart.q02_sellers_top10 ORDER BY item_revenue DESC NULLS LAST,seller_id LIMIT 1)
    UNION ALL
    SELECT 'q02.top_orders_delivered', 1124, orders_delivered FROM mart.q02_sellers_top10
        WHERE seller_id=(SELECT seller_id FROM mart.q02_sellers_top10 ORDER BY item_revenue DESC NULLS LAST,seller_id LIMIT 1)
    UNION ALL
    SELECT 'q02.top_units_delivered', 1148, units_delivered FROM mart.q02_sellers_top10
        WHERE seller_id=(SELECT seller_id FROM mart.q02_sellers_top10 ORDER BY item_revenue DESC NULLS LAST,seller_id LIMIT 1)
    UNION ALL
    SELECT 'q02.top_orders_all_statuses', 1132, orders_all_statuses FROM mart.q02_sellers_top10
        WHERE seller_id=(SELECT seller_id FROM mart.q02_sellers_top10 ORDER BY item_revenue DESC NULLS LAST,seller_id LIMIT 1)
    UNION ALL
    SELECT 'q02.top_units_all_statuses', 1156, units_all_statuses FROM mart.q02_sellers_top10
        WHERE seller_id=(SELECT seller_id FROM mart.q02_sellers_top10 ORDER BY item_revenue DESC NULLS LAST,seller_id LIMIT 1)
    UNION ALL
    SELECT 'q03.avg_order_gmv_rounded', 159.88, avg_order_gmv_rounded FROM mart.q03_average_order
    UNION ALL
    SELECT 'q03.n_order_gmv', 96478, n_order_gmv FROM mart.q03_average_order
    UNION ALL
    SELECT 'q03.avg_payment_amount_rounded', 159.86, avg_payment_amount_rounded FROM mart.q03_average_order
    UNION ALL
    SELECT 'q03.n_payment_amount', 96477, n_payment_amount FROM mart.q03_average_order
    UNION ALL
    SELECT 'q03.avg_source_rows_3dp', 1.142, round(avg_source_rows,3) FROM mart.q03_average_order
    UNION ALL
    SELECT 'q03.avg_units_3dp', 1.142, round(avg_units,3) FROM mart.q03_average_order
    UNION ALL
    SELECT 'q03.avg_distinct_product_seller_lines_3dp', 1.039, round(avg_distinct_product_seller_lines,3) FROM mart.q03_average_order
    UNION ALL
    SELECT 'q04.buyers_all_snapshot', 96096, buyers FROM mart.q04_buyers_repeat
    UNION ALL
    SELECT 'q04.repeat_buyers_all_snapshot', 2997, repeat_buyers FROM mart.q04_buyers_repeat
    UNION ALL
    SELECT 'q04.repeat_pct_all_snapshot_2dp', 3.12, repeat_buyer_pct_rounded FROM mart.q04_buyers_repeat
    UNION ALL
    SELECT 'q04.buyers_q1_window', 96090, buyers FROM mart.q04_buyers_repeat_q1_window
    UNION ALL
    SELECT 'q04.repeat_buyers_q1_window', 2987, repeat_buyers FROM mart.q04_buyers_repeat_q1_window
    UNION ALL
    SELECT 'q04.repeat_pct_q1_window_2dp', 3.11, repeat_buyer_pct_rounded FROM mart.q04_buyers_repeat_q1_window
    UNION ALL
    SELECT 'q05.categories', 74, count(*) FROM mart.q05_category_revenue
    UNION ALL
    SELECT 'q05.top_category_revenue', 1233131.72, max(item_revenue) FROM mart.q05_category_revenue
    UNION ALL
    SELECT 'q05.item_revenue', 13221498.11, sum(item_revenue) FROM mart.q05_category_revenue
    UNION ALL
    SELECT 'q05.unknown_category_members', 1, count(*) FROM mart.q05_category_revenue WHERE is_unknown
    UNION ALL
    SELECT 'q05.known_categories_missing_translation', 2, count(*) FROM mart.q05_category_revenue WHERE NOT is_unknown AND NOT is_translated
    UNION ALL
    SELECT 'reconciliation.both', 98665, sum(orders_count) FROM mart.v_payment_reconciliation WHERE payment_coverage='both'
    UNION ALL
    SELECT 'reconciliation.items_only', 1, sum(orders_count) FROM mart.v_payment_reconciliation WHERE payment_coverage='items_only'
    UNION ALL
    SELECT 'reconciliation.payments_only', 775, sum(orders_count) FROM mart.v_payment_reconciliation WHERE payment_coverage='payments_only'
    UNION ALL
    SELECT 'reconciliation.neither', 0, sum(orders_count) FROM mart.v_payment_reconciliation WHERE payment_coverage='neither'
    UNION ALL
    SELECT 'reconciliation.exact_mismatch_orders', 639, sum(exact_mismatch_orders) FROM mart.v_payment_reconciliation
    UNION ALL
    SELECT 'reconciliation.exact_signed_delta_sum', -1819.51, sum(exact_signed_delta_sum) FROM mart.v_payment_reconciliation
    UNION ALL
    SELECT 'reconciliation.exact_absolute_delta_sum', 7981.47, sum(exact_absolute_delta_sum) FROM mart.v_payment_reconciliation
    UNION ALL
    SELECT 'reconciliation.gt_001_mismatch_orders', 366, sum(gt_001_mismatch_orders) FROM mart.v_payment_reconciliation
    UNION ALL
    SELECT 'reconciliation.gt_001_signed_delta_sum', -1818.84, sum(gt_001_signed_delta_sum) FROM mart.v_payment_reconciliation
    UNION ALL
    SELECT 'reviews.pairs', 99224, count(*) FROM core.fact_review
    UNION ALL
    SELECT 'reviews.ids', 98410, count(*) FROM mart.v_review
    UNION ALL
    SELECT 'reviews.payload_conflicts', 0, count(*) FROM mart.v_review WHERE has_payload_conflict
)
SELECT metric_name, expected AS csv_reference, actual AS core_result,
       actual IS NOT NULL AND actual=expected AS ok,
       '8afb8691d866ef5f5ed465eb9111df521408e1b3d84408d5f0c03337477312c3'::text AS reference_manifest_sha256
FROM checks;

TABLE w10_control_results;
SELECT coalesce(bool_and(ok),false) AS w10_controls_pass FROM w10_control_results
\gset
\if :w10_controls_pass
\echo 'Pinned controls matched computed core/mart results; see externally verified input binding.'
\else
DO $w10_failed$ BEGIN
    RAISE EXCEPTION 'FAIL: pinned controls differ from core/mart results';
END $w10_failed$;
\endif
