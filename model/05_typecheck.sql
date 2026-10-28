-- PostgreSQL 16. Inspect text BEFORE any lossy cast; never modify raw.
-- Numeric is unconstrained in CONTRACT.md: extra fractional digits survive.
-- Reject non-finite/exponent/whitespace input explicitly; scale > 2 in money
-- is a warning in 30_quality.sql, not an implicit rounding operation.
CREATE TEMP TABLE capibara_type_errors (
    source_table text NOT NULL,
    source_column text NOT NULL,
    rule text NOT NULL,
    invalid_count bigint NOT NULL
) ON COMMIT DROP;

DO $typecheck$
DECLARE
    spec record;
    predicate text;
    failures text;
BEGIN
    FOR spec IN
        SELECT * FROM (VALUES
            ('orders', 'order_id', 'key'),
            ('orders', 'customer_id', 'key'),
            ('orders', 'order_status', 'key'),
            ('order_items', 'order_id', 'key'),
            ('order_items', 'order_item_id', 'required_integer'),
            ('order_items', 'product_id', 'key'),
            ('order_items', 'seller_id', 'key'),
            ('order_payments', 'order_id', 'key'),
            ('order_payments', 'payment_sequential', 'required_integer'),
            ('order_payments', 'payment_installments', 'integer'),
            ('order_reviews', 'review_id', 'key'),
            ('order_reviews', 'order_id', 'key'),
            ('order_reviews', 'review_score', 'integer'),
            ('products', 'product_id', 'key'),
            ('products', 'product_name_lenght', 'integer'),
            ('products', 'product_description_lenght', 'integer'),
            ('products', 'product_photos_qty', 'integer'),
            ('sellers', 'seller_id', 'key'),
            ('customers', 'customer_id', 'key'),
            ('customers', 'customer_unique_id', 'key'),
            ('product_category_translation', 'product_category_name', 'required_text'),
            ('order_items', 'price', 'numeric'),
            ('order_items', 'freight_value', 'numeric'),
            ('order_payments', 'payment_value', 'numeric'),
            ('products', 'product_weight_g', 'numeric'),
            ('products', 'product_length_cm', 'numeric'),
            ('products', 'product_height_cm', 'numeric'),
            ('products', 'product_width_cm', 'numeric'),
            ('orders', 'order_purchase_timestamp', 'timestamp'),
            ('orders', 'order_approved_at', 'timestamp'),
            ('orders', 'order_delivered_carrier_date', 'timestamp'),
            ('orders', 'order_delivered_customer_date', 'timestamp'),
            ('orders', 'order_estimated_delivery_date', 'timestamp'),
            ('order_items', 'shipping_limit_date', 'timestamp'),
            ('order_reviews', 'review_creation_date', 'timestamp'),
            ('order_reviews', 'review_answer_timestamp', 'timestamp')
        ) AS rules(source_table, source_column, rule)
    LOOP
        IF spec.rule = 'key' THEN
            predicate := format('%1$I IS NULL OR %1$I ~ %2$L',
                                spec.source_column, '^[[:space:]]*$');
        ELSIF spec.rule = 'required_text' THEN
            -- CONTRACT gives even '' the distinct identity 'pt:'.
            predicate := format('%I IS NULL', spec.source_column);
        ELSIF spec.rule IN ('integer', 'required_integer') THEN
            -- integer input checks bounds too; '1.5' must not round to 2.
            predicate := format(
                '%1$I IS NOT NULL AND (NOT (%1$I ~ %2$L) OR NOT pg_catalog.pg_input_is_valid(%1$I, %3$L))',
                spec.source_column, '^[+-]?[0-9]+$', 'integer');
            IF spec.rule = 'required_integer' THEN
                predicate := format('%I IS NULL OR (%s)', spec.source_column, predicate);
            END IF;
        ELSIF spec.rule = 'numeric' THEN
            -- Unconstrained numeric has finite storage/scale limits. The safe
            -- input validator checks them without casting the bad source text.
            predicate := format(
                '%1$I IS NOT NULL AND (NOT (%1$I ~ %2$L) OR NOT pg_catalog.pg_input_is_valid(%1$I, %3$L))',
                spec.source_column, '^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)$', 'numeric');
        ELSE
            -- No timezone suffix, infinity, timezone-dependent input or implicit
            -- fractional-second rounding. Chronology remains a separate warning.
            predicate := format(
                '%1$I IS NOT NULL AND (NOT (%1$I ~ %2$L) OR NOT pg_catalog.pg_input_is_valid(%1$I, %3$L))',
                spec.source_column,
                '^[0-9]{4}-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01]) ([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$',
                'timestamp without time zone');
        END IF;
        EXECUTE format(
            'INSERT INTO pg_temp.capibara_type_errors '
            'SELECT %L, %L, %L, count(*) FROM raw.%I WHERE %s HAVING count(*) > 0',
            spec.source_table, spec.source_column, spec.rule,
            spec.source_table, predicate);
    END LOOP;

    SELECT string_agg(format('raw.%I.%I [%s]: %s row(s)',
                            source_table, source_column, rule, invalid_count),
                      E'\n' ORDER BY source_table, source_column)
      INTO failures FROM pg_temp.capibara_type_errors;
    IF failures IS NOT NULL THEN
        RAISE EXCEPTION USING
            MESSAGE = 'Input type/key precheck failed before model casts',
            DETAIL = failures,
            HINT = 'Inspect the named raw columns read-only. Do not repair, reload or round raw in the build.';
    END IF;
END
$typecheck$;
