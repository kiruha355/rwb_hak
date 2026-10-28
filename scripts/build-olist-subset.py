#!/usr/bin/env python3
"""Prepare/load/verify a bounded real Olist subset, never the full fixture.

This deliberately stratified 1,000-order slice is not representative of Olist.
All source values and all children/referenced dimensions are preserved. CSVs and
PostgreSQL files stay outside Git. This tool never starts/stops PostgreSQL,
installs dependencies, touches the usual marketplace DB, or loads full Olist.
"""
import argparse
import collections
import csv
import hashlib
import heapq
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]
SIZE = 1000
DB = "rwb_olist_subset_1000_20261028"
CLUSTER = Path.home() / ".local/share/rwb-hak-dev/pg16-smoke-20261028/data"
SOCKET = CLUSTER.parent / "socket"
RUNTIME = Path.home() / ".local/share/rwb-hak-dev/olist-subset-1000-20261028"
REPORT = ROOT / "research/implementation-review-20261028"
MANDATORY = {"e481f51cbdc54678b7cc49136f2d6af7", "bfbd0f9bdef84302105ad712db648a6c"}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(source, runtime, report):
    pinned = json.loads((ROOT / "tests/model/input-manifest.lock.json").read_text())
    source = source.resolve()
    runtime = runtime.resolve()
    if runtime.is_relative_to(ROOT) or source == runtime:
        raise ValueError("Subset CSV runtime must be outside the repository and source")
    if (runtime / "csv").exists():
        raise ValueError("Refusing to overwrite an existing subset CSV directory")
    for entry in pinned["files"]:
        path = source / entry["file"]
        if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError("Full source pin mismatch: " + entry["file"])
    customer_buyer = {r["customer_id"]: r["customer_unique_id"]
                      for r in rows(source / "olist_customers_dataset.csv")}
    first_order, repeat_pairs, strata, smallest = {}, {}, {}, []
    status_counts, month_counts = collections.Counter(), collections.Counter()
    found_mandatory = set()
    count = 0
    for row in rows(source / "olist_orders_dataset.csv"):
        count += 1
        oid, cid = row["order_id"], row["customer_id"]
        rank = int(hashlib.sha256(oid.encode()).hexdigest(), 16)
        if len(smallest) < SIZE:
            heapq.heappush(smallest, (-rank, oid))
        elif rank < -smallest[0][0]:
            heapq.heapreplace(smallest, (-rank, oid))
        key = (row["order_purchase_timestamp"][:7], row["order_status"])
        if key not in strata or rank < strata[key][0]:
            strata[key] = (rank, oid)
        status_counts[key[1]] += 1
        month_counts[key[0]] += 1
        if oid in MANDATORY:
            found_mandatory.add(oid)
        buyer = customer_buyer[cid]
        if buyer in first_order and buyer not in repeat_pairs:
            repeat_pairs[buyer] = (first_order[buyer], oid)
        else:
            first_order.setdefault(buyer, oid)
    if count != 99441 or found_mandatory != MANDATORY:
        raise ValueError("Unexpected source orders or missing mandatory real examples")
    chosen_buyers = sorted(repeat_pairs, key=lambda b: hashlib.sha256(b.encode()).hexdigest())[:25]
    selected = set(MANDATORY) | {v[1] for v in strata.values()}
    for buyer in chosen_buyers:
        selected.update(repeat_pairs[buyer])
    guaranteed_count = len(selected)
    for _, oid in sorted(smallest, key=lambda v: -v[0]):
        if len(selected) >= SIZE:
            break
        selected.add(oid)
    if len(selected) != SIZE:
        raise ValueError("Expected exactly 1000 selected real orders")
    del first_order, repeat_pairs, customer_buyer, smallest
    csv_dir = runtime / "csv"
    csv_dir.mkdir(parents=True)
    customer_ids, product_ids, seller_ids = set(), set(), set()
    selected_statuses, selected_months = collections.Counter(), collections.Counter()
    entries = []
    for entry in pinned["files"]:
        table = entry["table"].split(".")[1]
        destination = csv_dir / entry["file"]
        n = 0
        with destination.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=entry["header"], lineterminator="\n")
            writer.writeheader()
            for row in rows(source / entry["file"]):
                keep = (row.get("order_id") in selected if table in {"orders", "order_items", "order_payments", "order_reviews"}
                        else row.get("product_id") in product_ids if table == "products"
                        else row.get("seller_id") in seller_ids if table == "sellers"
                        else row.get("customer_id") in customer_ids if table == "customers" else True)
                if not keep:
                    continue
                writer.writerow(row)
                n += 1
                if table == "orders":
                    customer_ids.add(row["customer_id"])
                    selected_statuses[row["order_status"]] += 1
                    selected_months[row["order_purchase_timestamp"][:7]] += 1
                elif table == "order_items":
                    product_ids.add(row["product_id"])
                    seller_ids.add(row["seller_id"])
        entries.append({**entry, "source_sha256": entry["sha256"], "source_rows": entry["rows"],
                        "sha256": sha(destination), "bytes": destination.stat().st_size, "rows": n})
    if sum(e["rows"] for e in entries) >= 10000:
        raise ValueError("Subset row budget unexpectedly exceeded")
    manifest = {
        "schema_version": 1, "scope": "real_olist_stratified_subset", "orders": SIZE,
        "population_orders": count, "representative": False, "full_olist_loaded": False,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "source": pinned["source"],
        "selection_algorithm": "v1: mandatory real example and missing-payment order; lowest SHA256(order_id) per observed purchase-month/status stratum; first two source-order rows for 25 repeat buyers with lowest SHA256(customer_unique_id); fill to 1000 with globally lowest SHA256(order_id). All children and referenced dimension rows, full tiny translation table. No extrapolation.",
        "mandatory_order_ids": sorted(MANDATORY), "guaranteed_orders_before_fill": guaranteed_count,
        "guaranteed_repeat_buyers": len(chosen_buyers),
        "selected_order_ids_sha256": hashlib.sha256("\n".join(sorted(selected)).encode()).hexdigest(),
        "population_status_counts": dict(sorted(status_counts.items())),
        "selected_status_counts": dict(sorted(selected_statuses.items())),
        "population_month_counts": dict(sorted(month_counts.items())),
        "selected_month_counts": dict(sorted(selected_months.items())),
        "source_pin_status": "all_8_full_source_SHA256_and_bytes_match",
        "status": "prepared_not_loaded", "files": entries,
    }
    write_json(report / "olist-subset-input.json", manifest)
    print(json.dumps({"status": manifest["status"], "orders": SIZE, "rows": sum(e["rows"] for e in entries)}))


def connect(database="postgres"):
    import psycopg2
    connection = psycopg2.connect(host=str(SOCKET), port=55416, user="a", dbname=database,
                                  application_name="rwb_bounded_real_olist_subset", connect_timeout=5)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('data_directory'), current_setting('listen_addresses'), current_setting('shared_buffers'), current_database()")
        data, addresses, buffers, actual_db = cursor.fetchone()
        if Path(data).resolve() != CLUSTER.resolve() or addresses or buffers != "8MB" or actual_db != database:
            connection.close()
            raise ValueError("Endpoint is not the authorized task-owned tiny Unix-socket cluster")
    connection.rollback()
    return connection


def load(runtime, report):
    from psycopg2 import sql
    manifest = json.loads((report / "olist-subset-input.json").read_text())
    conn = connect()
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DB,))
            if not cursor.fetchone():
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB)))
    finally:
        conn.close()
    conn = connect(DB)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT nspname FROM pg_namespace WHERE nspname IN ('raw','core','mart')")
            if cursor.fetchall():
                raise ValueError("Refusing to overwrite existing raw/core/mart schemas")
            cursor.execute("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace AND relkind IN ('r','p','v','m','S')")
            if cursor.fetchone()[0]:
                raise ValueError("Refusing to load into nonempty database")
            cursor.execute("CREATE SCHEMA raw")
            cursor.execute((ROOT / "scripts/init/02_raw_ddl.sql").read_text())
            for entry in manifest["files"]:
                path = runtime / "csv" / entry["file"]
                if sha(path) != entry["sha256"]:
                    raise ValueError("Subset CSV changed before load")
                table = sql.Identifier(*entry["table"].split("."))
                columns = sql.SQL(",").join(map(sql.Identifier, entry["header"]))
                query = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(table, columns)
                with path.open(encoding="utf-8", newline="") as stream:
                    cursor.copy_expert(query.as_string(conn), stream)
                cursor.execute(sql.SQL("UPDATE {} SET _source_file=%s").format(table), (entry["file"],))
        conn.commit()
    finally:
        conn.close()
    print("Loaded 8 bounded real CSVs into new task-owned subset DB; raw writers now paused")


def verify(runtime, report):
    manifest = json.loads((report / "olist-subset-input.json").read_text())
    spec = importlib.util.spec_from_file_location("subset_verify", ROOT / "scripts/verify-model.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    conn = connect(DB)
    try:
        results = module.compare_csv_rows(conn, manifest["files"], runtime / "csv")
        if any(r[k] for r in results for k in ("missing_in_raw", "extra_in_raw", "wrong_source_file")):
            raise ValueError("Subset CSV/raw mismatch: " + json.dumps(results))
    finally:
        conn.rollback()
        conn.close()
    output = {"status": "passed", "scope": "only the bounded real 1000-order subset",
              "method": "session-private temp tables; REPEATABLE READ READ ONLY source snapshot; bidirectional EXCEPT ALL; _source_file equality",
              "files": results, "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "input_manifest_sha256": sha(report / "olist-subset-input.json"),
              "verifier_sha256": sha(ROOT / "scripts/verify-model.py")}
    write_json(report / "olist-subset-raw-verification.json", output)
    print("8/8 subset CSV/raw multiset comparisons passed")


def validation_report(runtime, report):
    manifest = json.loads((report / "olist-subset-input.json").read_text())
    raw = json.loads((report / "olist-subset-raw-verification.json").read_text())
    builds = json.loads((report / "olist-subset-build.json").read_text())
    if raw["status"] != "passed" or len(builds["commands"]) != 4 or any(c["exit_code"] for c in builds["commands"]):
        raise ValueError("CSV/raw and all four model commands must pass first")
    export_spec = importlib.util.spec_from_file_location("subset_readonly_export", ROOT / "dashboard/subset/export_data.py")
    exporter = importlib.util.module_from_spec(export_spec)
    export_spec.loader.exec_module(exporter)
    conn = connect(DB)
    conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT count(*),count(*) FILTER (WHERE NOT ok AND severity='error'),count(*) FILTER (WHERE NOT ok AND severity='warning') FROM core.check_results")
            total, errors, warnings = cursor.fetchone()
            cursor.execute("SELECT check_name, expected, actual, severity FROM core.check_results WHERE NOT ok ORDER BY check_name")
            issues = [dict(zip(("check_name", "expected", "actual", "severity"), row)) for row in cursor.fetchall()]
            counts = {}
            for name, query in {
                "orders": "SELECT count(*) FROM mart.v_orders",
                "items": "SELECT count(*) FROM mart.v_order_items",
                "reviews": "SELECT count(*) FROM core.fact_review",
                "months": "SELECT count(DISTINCT month_start) FROM core.dim_date",
            }.items():
                cursor.execute(query)
                counts[name] = cursor.fetchone()[0]
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            answers = {}
            for name in ("q01", "q02", "q03", "q04", "q05"):
                sql_text = (ROOT / "answers" / (name + ".sql")).read_text()
                cursor.execute(sql_text)
                answers[name] = [dict(zip([c.name for c in cursor.description], row)) for row in cursor.fetchall()]
            payload = {}
            for name, query in exporter.QUERIES.items():
                cursor.execute(query)
                payload[name] = [dict(zip([c.name for c in cursor.description], row)) for row in cursor.fetchall()]
            delivery = {r["order_id"]: r for r in payload.pop("delivery")}
            for row in payload["orders"]:
                row.update(delivery[row["order_id"]])
            payload["months"] = [r["month_start"] for r in payload["months"]]
            data_hash = hashlib.sha256(exporter.canonical(json.loads(exporter.canonical(payload))).encode()).hexdigest()
    finally:
        conn.rollback()
        conn.close()
    if errors or counts["orders"] != SIZE:
        raise ValueError("Core invariants or subset order population failed")
    files = [ROOT / "model/CONTRACT.md", *module_stages()]
    result = {"kind": "olist_subset_validation", "status": "passed", "database": DB,
              "scope": {"kind": "olist_subset", "selected_orders": SIZE, "source_orders": manifest["population_orders"],
                        "selection": manifest["selection_algorithm"], "representative": False, "full_population_validated": False},
              "row_counts": counts, "data_sha256": data_hash, "csv_raw": {"status": "passed", "files_checked": len(raw["files"]),
                          "report_sha256": sha(report / "olist-subset-raw-verification.json")},
              "core_checks": {"total": total, "errors": errors, "warnings": warnings, "issues": issues},
              "code_sha256": {str(p.relative_to(ROOT)): sha(p) for p in files},
              "source_input_manifest_sha256": sha(report / "olist-subset-input.json"),
              "build_report_sha256": sha(report / "olist-subset-build.json"), "postgres_version": version,
              "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "not_run": ["full Olist database load", "full-population pinned controls", "representativeness or extrapolation"]}
    write_json(report / "olist-subset-validation.json", result)
    # Keep exact PostgreSQL numeric strings in published answer evidence.
    (report / "olist-subset-answers.json").write_text(json.dumps({"scope": result["scope"], "answers": answers},
               ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "core_checks": result["core_checks"], "row_counts": counts}))


def module_stages():
    return [ROOT / "model" / name for name in ("05_typecheck.sql", "10_dims.sql", "20_facts.sql", "30_quality.sql", "40_mart.sql", "50_answers.sql", "90_checks.sql")]


def rollback_check(report):
    """Inject an actual late SQL failure after all stages, then prove restore."""
    import psycopg2
    from psycopg2 import sql
    conn = connect(DB)
    def fingerprint():
        values = {}
        with conn.cursor() as cur:
            cur.execute("SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('raw','core','mart') AND c.relkind IN ('r','v','m','p') ORDER BY 1,2")
            tables = cur.fetchall()
            for schema, table in tables:
                expr = sql.SQL("to_jsonb(t) - 'checked_at'") if (schema, table) == ("core", "check_results") else sql.SQL("to_jsonb(t)")
                cur.execute(sql.SQL("SELECT count(*),md5(coalesce(string_agg(v::text,'' ORDER BY v::text),'')) FROM (SELECT {} v FROM {} t) q").format(expr,sql.Identifier(schema, table)))
                values[schema + "." + table] = list(cur.fetchone())
        conn.rollback()
        return values
    before = fingerprint()
    conn.set_session(isolation_level="REPEATABLE READ")
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL capibara.raw_reload_paused='1'; SET LOCAL search_path=pg_catalog,pg_temp; SET LOCAL DateStyle='ISO,YMD'; SET LOCAL TimeZone='UTC'; SELECT pg_advisory_xact_lock(1667330674,1)")
            for path in [ROOT / "model/00_schemas.sql", *module_stages()]:
                cur.execute(path.read_text())
            cur.execute("SELECT 1/0 /* deliberate late subset rollback sentinel */")
    except psycopg2.Error as error:
        code, diagnostic = error.pgcode, error.pgerror
        conn.rollback()
        if code != "22012":
            raise
    else:
        conn.rollback()
        raise ValueError("Deliberate late failure was not detected")
    after = fingerprint()
    conn.close()
    if before != after:
        raise ValueError("Late-failure rollback changed committed raw/core/mart content")
    write_json(report / "olist-subset-rollback.json", {"status": "passed", "scope": "real 1000-order subset only",
               "method": "all build stages executed in one transaction, deliberate SELECT 1/0 after invariant checks, actual SQLSTATE 22012; rollback then raw/core/mart row-count and sorted content hashes match",
               "sqlstate": code, "diagnostic": diagnostic, "relations": len(before), "fingerprints": after})
    print("Late actual SQLSTATE 22012 rolled back; all raw/core/mart fingerprints match")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "load", "verify", "build", "report", "rollback-check"))
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--runtime-dir", type=Path, default=RUNTIME)
    parser.add_argument("--report-dir", type=Path, default=REPORT)
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare(args.source_dir, args.runtime_dir, args.report_dir)
    elif args.phase == "load":
        load(args.runtime_dir, args.report_dir)
    elif args.phase == "verify":
        verify(args.runtime_dir, args.report_dir)
    elif args.phase == "report":
        validation_report(args.runtime_dir, args.report_dir)
    elif args.phase == "rollback-check":
        rollback_check(args.report_dir)
    else:
        env = {**os.environ, "RWB_RAW_RELOAD_PAUSED": "1", "RWB_DB_MODE": "host", "PGHOST": str(SOCKET),
               "PGPORT": "55416", "PGDATABASE": DB, "PGUSER": "a",
               "PATH": "/opt/homebrew/opt/postgresql@16/bin:" + os.environ.get("PATH", "")}
        for key in ("PGSERVICE", "PGSERVICEFILE", "DATABASE_URL"):
            env.pop(key, None)
        conn = connect(DB)
        conn.close()
        outcomes = []
        for mode in ("build", "check", "answers", "rebuild-check"):
            result = subprocess.run(["bash", "scripts/build-model.sh", mode], cwd=ROOT, env=env, text=True, capture_output=True)
            logfile = args.runtime_dir / (mode + ".log")
            logfile.write_text(result.stdout + result.stderr)
            outcomes.append({"command": "bash scripts/build-model.sh " + mode, "exit_code": result.returncode,
                             "log_sha256": sha(logfile)})
            write_json(args.report_dir / "olist-subset-build.json", {"scope": "real_olist_1000_order_subset_only", "commands": outcomes,
                        "full_pinned_controls": "not_run; subset is not full Olist population", "completed_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            print(mode, result.returncode, flush=True)
            if result.returncode:
                print(result.stdout[-12000:] + result.stderr[-6000:], file=sys.stderr)
                raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
