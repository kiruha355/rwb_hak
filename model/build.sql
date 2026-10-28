-- Entry point: bash scripts/build-model.sh build (or make build).
-- psql -X -1 -v ON_ERROR_STOP=1 owns the single transaction, including checks.
-- The wrapper establishes the raw reload barrier, isolation and advisory lock.
\set ON_ERROR_STOP on
DO $build_guard$
BEGIN
    IF current_setting('transaction_isolation') <> 'repeatable read'
       OR current_setting('capibara.raw_reload_paused', true) IS DISTINCT FROM '1'
    THEN
        RAISE EXCEPTION 'Use scripts/build-model.sh with an exclusive raw reload phase; see docs/build-runbook.md';
    END IF;
END
$build_guard$;

\ir 00_schemas.sql
\ir 05_typecheck.sql
\ir 10_dims.sql
\ir 20_facts.sql
\ir 30_quality.sql
\ir 40_mart.sql
\ir 50_answers.sql
\ir 90_checks.sql
\echo [capibara] All build stages and invariant checks completed; psql commits on successful exit.
