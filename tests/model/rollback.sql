-- Run only through validate-lifecycle.sh, on a dedicated validation DB.
-- psql -X -1 owns the transaction. The final deliberate error MUST roll back.
\set ON_ERROR_STOP on
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET LOCAL capibara.raw_reload_paused='1';
SET LOCAL lock_timeout='5s';
SET LOCAL statement_timeout='10min';
SET LOCAL DateStyle='ISO,YMD';
SET LOCAL TimeZone='UTC';
DO $guard$
BEGIN
 IF NOT pg_try_advisory_xact_lock(1667330674,1) THEN
  RAISE EXCEPTION 'Another cooperating model command is active';
 END IF;
END;
$guard$;
\ir ../../model/build.sql
DO $failure$
BEGIN
 RAISE EXCEPTION 'W11_INJECTED_LATE_FAILURE_AFTER_ALL_CHECKS';
END;
$failure$;
