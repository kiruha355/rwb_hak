#!/usr/bin/env python3
"""Plan or run isolated model fixtures, or compare pinned CSV content to raw.

Default --plan uses no database. Execution requires an existing, explicitly
configured PostgreSQL connection; this tool never starts services or loads raw.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/model/fixtures"
STAGES = ["05_typecheck.sql", "10_dims.sql", "20_facts.sql", "30_quality.sql", "40_mart.sql", "50_answers.sql", "90_checks.sql"]


def stages():
    return [ROOT / "model" / name for name in STAGES]


def schema_sql(text, schemas):
    """Rebind trusted repository fragments, including schema names in dynamic SQL."""
    for original, target in schemas.items():
        if not re.fullmatch(r"w11_(raw|core|mart)_[a-f0-9]{12}", target):
            raise ValueError("Unsafe test schema")
        text = text.replace(original + ".", target + ".")
    if re.search(r"\b(raw|core|mart)\s*\.", text, re.IGNORECASE):
        raise ValueError("Unrebound live schema reference")
    # PL/pgSQL BEGIN/END blocks are valid. Fragments never commit or use psql.
    if re.search(r"^\s*(COMMIT|END\s+TRANSACTION|ROLLBACK|\\)", text, re.IGNORECASE | re.MULTILINE):
        raise ValueError("Fixture fragment must not own the transaction or use psql commands")
    return text


def inventory():
    return json.loads((FIXTURES / "cases.json").read_text(encoding="utf-8"))


def plan():
    cases = inventory()
    names = [c["name"] for c in cases]
    if len(names) != len(set(names)) or not cases or "error_code" in cases[0]:
        raise ValueError("Fixture inventory needs unique names and a positive baseline first")
    missing = [str(p.relative_to(ROOT)) for p in stages() if not p.is_file()]
    for case in cases:
        if bool(case.get("error_code")) != bool(case.get("error_text")):
            raise ValueError(f"{case['name']}: require exact SQLSTATE and diagnostic text together")
        if case.get("assert") and not (FIXTURES / case["assert"]).is_file():
            raise ValueError(f"Missing assertion: {case['assert']}")
    return {"status": "pending_db_execution", "cases": names, "missing_stages": missing,
            "scope": "unique w11_* schemas in one transaction; all changes rolled back"}


def connect(env_name, fixtures):
    try:
        import psycopg2
    except ImportError:
        raise ValueError("psycopg2 unavailable; use the existing approved dev environment; DB execution pending")
    dsn = os.environ.get(env_name)
    if not dsn:
        raise ValueError(f"Set connection using environment variable {env_name}; never put credentials in artifacts")
    try:
        connection = psycopg2.connect(dsn, connect_timeout=5)
    except psycopg2.Error:
        raise ValueError("PostgreSQL connection failed; connection details omitted; DB execution pending") from None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_setting('server_version_num')::integer")
            database, version = cursor.fetchone()
            if version < 160000:
                raise ValueError("PostgreSQL 16+ required")
            if fixtures and database in {"marketplace", "postgres", "template0", "template1"}:
                raise ValueError("Fixtures require a dedicated test database, not marketplace/postgres/templates")
        connection.rollback()
        connection.set_session(isolation_level="REPEATABLE READ", readonly=not fixtures)
        return connection
    except BaseException:
        connection.close()
        raise


def run_fixtures(env_name):
    report = plan()
    if report["missing_stages"]:
        raise ValueError("Missing stages: " + ", ".join(report["missing_stages"]))
    import psycopg2
    connection = connect(env_name, fixtures=True)
    suffix = uuid.uuid4().hex[:12]
    schemas = {s: f"w11_{s}_{suffix}" for s in ("raw", "core", "mart")}
    results = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL search_path=pg_catalog,pg_temp; SET LOCAL statement_timeout='60s'; SET LOCAL lock_timeout='3s'; SET LOCAL DateStyle='ISO,YMD'; SET LOCAL TimeZone='UTC'")
            for schema in schemas.values():
                cursor.execute(f'CREATE SCHEMA "{schema}"')
            def execute(text):
                cursor.execute(schema_sql(text, schemas))
            execute((ROOT / "scripts/init/02_raw_ddl.sql").read_text())
            execute((FIXTURES / "base.sql").read_text())
            for case in inventory():
                cursor.execute("SAVEPOINT fixture_case")
                step = "input mutation"
                outcome = None
                try:
                    if case.get("before"):
                        execute(case["before"])
                    for stage in stages():
                        step = stage.name
                        execute(stage.read_text())
                    if case.get("after"):
                        step = "core mutation"
                        execute(case["after"])
                        step = "rerun invariant checks"
                        execute("SELECT core.run_checks()")
                    if case.get("error_code"):
                        raise ValueError(f"{case['name']}: expected failure was NOT detected")
                    step = "fixture assertions"
                    if case.get("assert"):
                        execute((FIXTURES / case["assert"]).read_text())
                    if case.get("assert_sql"):
                        execute(case["assert_sql"])
                    if case.get("warning"):
                        cursor.execute(f"SELECT ok,severity FROM {schemas['core']}.check_results WHERE check_name=%s", (case["warning"],))
                        if cursor.fetchone() != (False, "warning"):
                            raise ValueError(f"{case['name']}: required warning not recorded")
                    outcome = {"case": case["name"], "result": "passed", "method": "PostgreSQL isolated fixture"}
                except psycopg2.Error as error:
                    diagnostic = error.pgerror or str(error)
                    if error.pgcode != case.get("error_code") or case.get("error_text", "") not in diagnostic:
                        raise ValueError(f"{case['name']} at {step}: unexpected SQLSTATE {error.pgcode}: {diagnostic}") from error
                    # Full diagnostic is deliberately retained: result rows roll back.
                    outcome = {"case": case["name"], "result": "expected_failure_detected", "step": step,
                               "sqlstate": error.pgcode, "diagnostic": diagnostic}
                finally:
                    cursor.execute("ROLLBACK TO SAVEPOINT fixture_case")
                    cursor.execute("RELEASE SAVEPOINT fixture_case")
                results.append(outcome)
                # Verify rollback of each attempt to an empty test core.
                cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema=%s", (schemas["core"],))
                if cursor.fetchone()[0] != 0:
                    raise ValueError("Fixture rollback left core objects behind")
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_namespace WHERE nspname=ANY(%s)", (list(schemas.values()),))
            if cursor.fetchone()[0] != 0:
                raise ValueError("Outer rollback left test schemas behind")
        return {"status": "passed", "method": "isolated fixture execution only; not pinned full-model acceptance",
                "cases": results, "rollback": "test schemas absent after rollback",
                "stage_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in stages()}}
    finally:
        connection.rollback()
        connection.close()


def compare_csv_rows(connection, entries, data_dir):
    """Compare source rows in READ ONLY; prepare only session temp DDL first.

    PostgreSQL forbids CREATE TEMP in READ ONLY. A separate setup transaction
    creates empty session-private tables; the source snapshot is then acquired
    in REPEATABLE READ READ ONLY. No source/model object is written.
    """
    from psycopg2 import sql
    connection.set_session(readonly=False)
    try:
        with connection.cursor() as cursor:
            for index, entry in enumerate(entries):
                definitions = sql.SQL(",").join(
                    sql.SQL("{} text").format(sql.Identifier(c)) for c in entry["header"])
                cursor.execute(sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT PRESERVE ROWS").format(
                    sql.Identifier(f"w11_csv_{index}"), definitions))
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    connection.set_session(isolation_level="REPEATABLE READ", readonly=True)
    results = []
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout='120s'; SET LOCAL lock_timeout='3s'")
        for index, entry in enumerate(entries):
            columns = sql.SQL(",").join(map(sql.Identifier, entry["header"]))
            temp = sql.Identifier(f"w11_csv_{index}")
            raw = sql.Identifier(*entry["table"].split("."))
            query = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(temp, columns)
            with (data_dir / entry["file"]).open(encoding="utf-8-sig", newline="") as stream:
                cursor.copy_expert(query.as_string(connection), stream)
            def differences(left, right):
                cursor.execute(sql.SQL("SELECT count(*) FROM (SELECT {} FROM {} EXCEPT ALL SELECT {} FROM {}) d").format(columns,left,columns,right))
                return cursor.fetchone()[0]
            missing = differences(temp, raw)
            extra = differences(raw, temp)
            cursor.execute(sql.SQL("SELECT count(*) FROM {} WHERE _source_file IS DISTINCT FROM %s").format(raw), (entry["file"],))
            wrong_lineage = cursor.fetchone()[0]
            results.append({"file": entry["file"], "table": entry["table"], "csv_rows": entry["rows"],
                            "missing_in_raw": missing, "extra_in_raw": extra, "wrong_source_file": wrong_lineage})
    return results


def raw_inputs(env_name, data_dir):
    if os.environ.get("RWB_RAW_RELOAD_PAUSED") != "1":
        raise ValueError("RWB_RAW_RELOAD_PAUSED=1 required after all raw writers are paused; snapshot isolation alone is insufficient")
    spec = importlib.util.spec_from_file_location("input_manifest", ROOT / "scripts/input-manifest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    pinned = module.load_manifest(module.PIN)
    before = module.collect(data_dir, pinned)
    failures = module.compare(before, pinned)
    if failures:
        raise ValueError("Pinned CSV mismatch: " + "; ".join(failures))
    connection = connect(env_name, fixtures=False)
    try:
        results = compare_csv_rows(connection, pinned["files"], data_dir)
        if module.compare(module.collect(data_dir, pinned), before):
            raise ValueError("CSV changed during raw comparison")
        if any(r[k] for r in results for k in ("missing_in_raw", "extra_in_raw", "wrong_source_file")):
            raise ValueError("CSV/raw multiset mismatch: " + json.dumps(results))
        return {"status": "passed", "method": "pinned CSV vs raw business columns: bidirectional EXCEPT ALL, PG CSV NULL semantics",
                "core_checked": False, "files": results}
    finally:
        connection.rollback()
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--run-fixtures", action="store_true")
    mode.add_argument("--raw-inputs", action="store_true")
    parser.add_argument("--dsn-env", help="environment variable containing libpq DSN; value is never printed")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args(argv)
    try:
        if args.run_fixtures:
            result = run_fixtures(args.dsn_env or "RWB_TEST_DSN")
        elif args.raw_inputs:
            result = raw_inputs(args.dsn_env or "RWB_VALIDATION_DSN", args.data_dir)
        else:
            result = plan()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, ImportError) as error:
        print(f"verify-model: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
