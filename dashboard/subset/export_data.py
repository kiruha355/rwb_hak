#!/usr/bin/env python3
"""Export an existing model snapshot. Never builds, reloads or writes the DB."""
import argparse
import base64
import datetime as dt
import decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
QUERIES = {
    "orders": """SELECT order_id, customer_unique_id, order_status, customer_state,
        order_purchase_timestamp, order_delivered_carrier_date,
        order_delivered_customer_date, order_estimated_delivery_date,
        is_revenue, is_delivered, source_rows_count, price_valid_count,
        item_revenue, order_gmv, payments_count, payment_valid_count, payment_amount
        FROM mart.v_orders ORDER BY order_id""",
    "delivery": """SELECT order_id, is_late_calendar_day, is_late_timestamp,
        purchase_to_delivery_days FROM mart.v_order_delivery_variants ORDER BY order_id""",
    "items": """SELECT order_id, order_item_id, seller_id, category_key,
        category_name_pt, category_name_en, is_unknown_category,
        is_category_translated, price, freight_value
        FROM mart.v_order_items ORDER BY order_id, order_item_id""",
    "reviews": """SELECT r.order_id, r.review_id, r.review_score,
        v.has_payload_conflict FROM core.fact_review r
        JOIN mart.v_review v ON v.review_id=r.review_id ORDER BY r.order_id,r.review_id""",
    "months": "SELECT DISTINCT month_start FROM core.dim_date ORDER BY month_start",
}


def encode(value):
    if isinstance(value, decimal.Decimal):
        if not value.is_finite():
            raise ValueError("non-finite model numeric")
        return format(value, "f")  # preserve precision, never exponent notation
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()  # source timestamps have no timezone
    raise TypeError(type(value).__name__)


def canonical(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=encode)


def write_export(payload, target, html_target=None):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(canonical(payload) + "\n", encoding="utf-8")
    if html_target:
        template = (ROOT / "dashboard/subset/template.html").read_text(encoding="utf-8")
        start, end = "<!-- DATA_START -->", "<!-- DATA_END -->"
        safe = canonical(payload).replace("<", "\\u003c").replace("&", "\\u0026")
        if payload.get("manifest", {}).get("mode") != "demo":
            safe = base64.b64encode(gzip.compress(canonical(payload).encode("utf-8"), mtime=0)).decode("ascii")
            replacement = '<script id="embedded-data" type="application/json" data-encoding="gzip-base64">' + safe + '</script>'
        else:
            replacement = '<script id="embedded-data" type="application/json">' + safe + '</script>'
        rendered = template.split(start)[0] + start + replacement + end + template.split(end)[1]
        if payload.get("manifest", {}).get("mode") != "demo":
            # A real export must never switch back to the hand-authored sample.
            demo_start = rendered.find("const DEMO_DATA=")
            embedded_start = rendered.find("readEmbedded().then(", demo_start)
            if demo_start >= 0 and embedded_start > demo_start:
                rendered = rendered[:demo_start] + rendered[embedded_start:]
            rendered = rendered.replace("$('demo-button').onclick=()=>load(DEMO_DATA);",
                                        "$('demo-button').onclick=()=>load(embedded);")
            rendered = rendered.replace('id="demo-button">Учебный набор',
                                        'id="demo-button">Исходная выгрузка')
        Path(html_target).write_text(rendered, encoding="utf-8")


def subset_validation(path, data, database):
    """Bind a bounded real-data pipeline report to this exported model snapshot.

    This explicitly does not establish full-population Olist acceptance.
    """
    content = Path(path).read_bytes()
    report = json.loads(content)
    if report.get("kind") != "olist_subset_validation" or report.get("status") != "passed":
        raise ValueError("a passed Olist subset validation report is required")
    if report.get("database") != database:
        raise ValueError("validation report belongs to a different database")
    scope = report.get("scope", {})
    counts = {k: len(data[k]) for k in ("orders", "items", "reviews", "months")}
    if (scope.get("kind") != "olist_subset"
            or scope.get("full_population_validated") is not False
            or scope.get("selected_orders") != counts["orders"]
            or not isinstance(scope.get("source_orders"), int)
            or scope["source_orders"] < counts["orders"]
            or report.get("row_counts") != counts):
        raise ValueError("subset scope/row counts do not match the exported model")
    if (report.get("csv_raw", {}).get("status") != "passed"
            or report.get("core_checks", {}).get("errors") != 0):
        raise ValueError("subset CSV/raw and model checks have not passed")
    if report.get("data_sha256") != hashlib.sha256(canonical(data).encode()).hexdigest():
        raise ValueError("model payload changed since subset validation")
    hashes = report.get("code_sha256", {})
    required = {"model/CONTRACT.md", *("model/" + name for name in
                ("05_typecheck.sql", "10_dims.sql", "20_facts.sql", "30_quality.sql",
                 "40_mart.sql", "50_answers.sql", "90_checks.sql"))}
    if not required.issubset(hashes):
        raise ValueError("subset validation must identify every model stage")
    for name, digest in hashes.items():
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT.resolve()) or not name.startswith("model/"):
            raise ValueError("unexpected path in subset model hashes")
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("model changed since subset validation: " + name)
    return {"validation_status": "subset_checked_not_full_olist",
            "status": "real_subset_checked", "scope": scope,
            "validation_report_sha256": hashlib.sha256(content).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="local JSON output")
    parser.add_argument("--dataset-label", required=True, help="honest human source label")
    parser.add_argument("--html", help="optional standalone HTML with this export embedded")
    parser.add_argument("--validation-report", help="optional passed real-subset report; never a full Olist assertion")
    args = parser.parse_args()
    # Only this explicit action connects. --help/import never touches the DB.
    import psycopg2
    with psycopg2.connect(os.environ.get("DATABASE_URL", ""), application_name="capibara_readonly_export") as conn:
        conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '60s'")
            cur.execute("SELECT current_timestamp, current_setting('server_version'), current_setting('transaction_read_only'), current_database()")
            snapshot_time, version, readonly, database = cur.fetchone()
            if readonly != "on":
                raise RuntimeError("read-only transaction required")
            data = {}
            for name, query in QUERIES.items():
                cur.execute(query)
                columns = [c.name for c in cur.description]
                data[name] = [dict(zip(columns, row)) for row in cur.fetchall()]
    deliveries = {r["order_id"]: r for r in data.pop("delivery")}
    if len(deliveries) != len(data["orders"]):
        raise ValueError("delivery/order coverage mismatch")
    for row in data["orders"]:
        row.update(deliveries[row["order_id"]])
    data["months"] = [r["month_start"] for r in data["months"]]
    # Materialize Decimal/date values before hashing the actual payload.
    data = json.loads(canonical(data))
    files = ["model/CONTRACT.md", "model/40_mart.sql", "model/50_answers.sql", "dashboard/subset/export_data.py"]
    manifest = {
        "schema_version": 1, "mode": "model_export", "dataset_label": args.dataset_label,
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "transaction_at": snapshot_time.isoformat(), "postgres_version": version,
        "method": "psycopg2; REPEATABLE READ READ ONLY; SELECT core/mart only",
        "status": "exported_not_validated", "validation_status": "not_evaluated",
        "timestamp_semantics": "source timestamp without timezone; no conversion",
        "currency": "BRL (Olist context assumption)",
        "row_counts": {k: len(v) for k, v in data.items()},
        "query_sha256": hashlib.sha256(canonical(QUERIES).encode()).hexdigest(),
        "data_sha256": hashlib.sha256(canonical(data).encode()).hexdigest(),
        "files_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in files},
        "sources": ["mart.v_orders", "mart.v_order_delivery_variants", "mart.v_order_items",
                    "core.fact_review", "mart.v_review", "core.dim_date"],
    }
    try:
        manifest["checkout_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        manifest["checkout_head"] = None
    if args.validation_report:
        manifest.update(subset_validation(args.validation_report, data, database))
    write_export({"manifest": manifest, **data}, args.output, args.html)
    print(f"Exported {len(data['orders'])} orders; status={manifest['status']}")


if __name__ == "__main__":
    main()
