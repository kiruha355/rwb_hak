-- Reset ONLY this model's named objects. Preserve the schemas and their grants.
-- RESTRICT is intentional: an unowned dependent view/FK/function blocks the
-- transaction with PostgreSQL's dependency detail. Never replace it with CASCADE.
-- All drops are transactional, so a later type/constraint/check error restores
-- the previously committed model. No raw object or data is altered here.
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;

DROP FUNCTION IF EXISTS core.run_checks() RESTRICT;

-- Drop the entire known view graph in one statement; internal dependencies are
-- among objects explicitly named here. New views must join this owned inventory.
DROP VIEW IF EXISTS
    mart.q01_revenue_monthly,
    mart.q02_sellers_top10,
    mart.q03_average_order,
    mart.q04_buyers_repeat,
    mart.q04_buyers_repeat_q1_window,
    mart.q05_category_revenue,
    mart.q06_price_history,
    mart.q07_delivery_by_state,
    mart.q08_status_snapshot,
    mart.q09_payments_2018_by_state,
    mart.q09_payment_methods,
    mart.q10_review_delivery,
    mart.q10_review_coverage,
    mart.v_order_delivery_variants,
    mart.v_review_weighting,
    mart.v_review,
    mart.v_review_payload_variants,
    mart.v_payment_reconciliation,
    mart.v_order_payment_reconciliation,
    mart.v_order_items,
    mart.v_orders
RESTRICT;

-- Likewise, the fact/dimension FK graph is removed as one explicit group.
DROP TABLE IF EXISTS
    core.check_results,
    core.data_issues,
    mart.metric_definitions,
    core.fact_review,
    core.fact_payment,
    core.fact_order_item,
    core.fact_order,
    core.dim_category_version,
    core.model_release,
    core.dim_product,
    core.dim_category,
    core.dim_seller,
    core.dim_customer_context,
    core.dim_customer,
    core.dim_order_status,
    core.dim_date
RESTRICT;

-- history.* is persistent source: never drop it during an ordinary rebuild.
