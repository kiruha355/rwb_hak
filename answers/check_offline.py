#!/usr/bin/env python3
"""Parse/bind W-10 SQL and test tiny synthetic cases in existing DuckDB.

This does not run PostgreSQL, load Olist/CSV, execute core DDL or prove core
results. DuckDB's NUMERIC/AVG and SQL dialect differ from PostgreSQL. No
installation, service, network, fixture directory or persistent DB is created.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SQL_PATHS = ("model/40_mart.sql", "model/50_answers.sql")


def run() -> dict:
    import duckdb  # Existing optional tool; this script never installs it.

    db = duckdb.connect(":memory:", config={"threads": "1", "memory_limit": "128MB"})
    checks: list[str] = []

    def check(name: str, condition: bool) -> None:
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    def row(query: str, params=None) -> dict:
        cursor = db.execute(query, params or [])
        values = cursor.fetchone()
        if values is None:
            raise AssertionError("expected row: " + query)
        return dict(zip((col[0] for col in cursor.description), values))

    parsed_counts = {}
    for relative in SQL_PATHS:
        sql = (ROOT / relative).read_text()
        statements = db.extract_statements(sql)
        parsed_counts[relative] = len(statements)
        check(relative + ": parsed nonempty", bool(statements))
        clean = re.sub(r"--[^\n]*", "", sql)
        check(relative + ": no raw relation", re.search(r"\braw\s*\.", clean, re.I) is None)
        check(relative + ": no transaction/reset ownership", re.search(
            r"\b(BEGIN|COMMIT|ROLLBACK|TRUNCATE|DROP|ALTER)\b", clean, re.I) is None)
        for statement in statements:
            statement_sql = re.sub(r"--[^\n]*", "", statement.query).strip()
            check(relative + ": allowed statement " + str(statement.type),
                  str(statement.type) in {"StatementType.CREATE", "StatementType.INSERT"}
                  or (str(statement.type) == "StatementType.ALTER" and statement_sql.upper().startswith("COMMENT ON ")))
        created = re.findall(r"\bCREATE\s+(?:TABLE|VIEW)\s+([\w.]+)", clean, re.I)
        check(relative + ": writes only mart", bool(created) and all(name.startswith("mart.") for name in created))
        inserted = re.findall(r"\bINSERT\s+INTO\s+([\w.]+)", clean, re.I)
        check(relative + ": metadata INSERT target only", all(name == "mart.metric_definitions" for name in inserted))

    baseline = json.loads((ROOT / "answers/baseline-manifest.json").read_text())
    audit_bytes = (ROOT / baseline["baseline_audit_manifest"]).read_bytes()
    audit = json.loads(audit_bytes)
    check("CSV reference manifest bytes pinned, not live DB binding", hashlib.sha256(audit_bytes).hexdigest()
          == baseline["baseline_audit_manifest_sha256"])
    check("baseline copies exactly eight source CSV hashes", len(baseline["files"]) == 8
          and {f["path"]:f["sha256"] for f in baseline["files"]}
          == {f["path"]:f["sha256"] for f in audit["files"]})
    check("control oracle carries matching manifest identity", (ROOT / "answers/control.sql").read_text().count(
          baseline["baseline_audit_manifest_sha256"]) == 2)

    # Deliberately tiny interface fixture. It is not an alternate core builder.
    db.execute("""
        CREATE SCHEMA core; CREATE SCHEMA mart;
        CREATE TABLE core.dim_order_status(order_status VARCHAR PRIMARY KEY, is_revenue BOOLEAN);
        CREATE TABLE core.dim_date(date_day DATE, month_start DATE);
        CREATE TABLE core.dim_category(category_key VARCHAR PRIMARY KEY, name_pt VARCHAR, name_en VARCHAR,
                                       is_unknown BOOLEAN, is_translated BOOLEAN);
        CREATE TABLE core.dim_product(product_id VARCHAR PRIMARY KEY, category_key VARCHAR);
        CREATE TABLE core.dim_seller(seller_id VARCHAR PRIMARY KEY, seller_city VARCHAR, seller_state VARCHAR);
        CREATE TABLE core.fact_order(
          order_id VARCHAR PRIMARY KEY, customer_id VARCHAR, customer_unique_id VARCHAR, order_status VARCHAR,
          order_purchase_timestamp TIMESTAMP, order_approved_at TIMESTAMP,
          order_delivered_carrier_date TIMESTAMP, order_delivered_customer_date TIMESTAMP,
          order_estimated_delivery_date TIMESTAMP, customer_city VARCHAR, customer_state VARCHAR);
        CREATE TABLE core.fact_order_item(
          order_id VARCHAR, order_item_id INTEGER, product_id VARCHAR, seller_id VARCHAR,
          price DECIMAL(18,4), freight_value DECIMAL(18,4), shipping_limit_at TIMESTAMP,
          PRIMARY KEY(order_id, order_item_id));
        CREATE TABLE core.fact_payment(
          order_id VARCHAR, payment_sequential INTEGER, payment_value DECIMAL(18,4),
          PRIMARY KEY(order_id, payment_sequential));
        CREATE TABLE core.fact_review(
          review_id VARCHAR, order_id VARCHAR, review_score INTEGER, review_comment_title VARCHAR,
          review_comment_message VARCHAR, review_creation_date TIMESTAMP, review_answer_timestamp TIMESTAMP,
          PRIMARY KEY(review_id, order_id));
    """)
    statuses = ["delivered", "shipped", "canceled", "unavailable", "invoiced", "processing", "created", "approved"]
    db.executemany("INSERT INTO core.dim_order_status VALUES (?,?)", [(s, s == "delivered") for s in statuses])
    day = dt.date(2016, 9, 1)
    calendar = []
    while day < dt.date(2018, 9, 1):
        calendar.append((day, day.replace(day=1)))
        day += dt.timedelta(days=1)
    db.executemany("INSERT INTO core.dim_date VALUES (?,?)", calendar)
    db.execute("""
      INSERT INTO core.dim_category VALUES
        ('unknown',NULL,NULL,true,false), ('pt:a','a','translated a',false,true),
        ('pt:missing','missing',NULL,false,false), ('pt:unused','unused','unused translation',false,true);
      INSERT INTO core.dim_product VALUES ('p1','pt:a'), ('p2','pt:missing'), ('p3','unknown');
      INSERT INTO core.dim_seller VALUES ('s1','source / dirty','SP'), ('s2','city2','RJ');
    """)
    # Bind the actual SQL, without rewriting its expressions for this engine.
    for relative in SQL_PATHS:
        db.execute((ROOT / relative).read_text())
    check("metric registry has required nonempty fields", db.execute("""
      SELECT count(*) > 0 AND bool_and(length(grain)>0 AND length(formula_sql)>0
        AND length(status_rule)>0 AND length(time_basis)>0 AND length("window")>0
        AND length(denominator)>0 AND length(null_policy)>0 AND length(unit)>0
        AND length(additive_over)>0 AND length(non_additive_over)>0)
      FROM mart.metric_definitions
    """).fetchone()[0])
    empty = row("SELECT * FROM mart.q03_average_order")
    check("empty average is unknown", empty["n_delivered_orders"] == 0 and empty["avg_order_gmv"] is None)
    check("empty buyers ratio is unknown", row("SELECT * FROM mart.q04_buyers_repeat")["repeat_buyer_ratio"] is None)
    check("calendar is 24 months before any orders", db.execute("SELECT count(*) FROM mart.q01_revenue_monthly").fetchone()[0] == 24)
    check("empty calendar revenue is measured zero", db.execute("SELECT bool_and(item_revenue=0) FROM mart.q01_revenue_monthly").fetchone()[0])
    check("empty categories have unknown percentage", db.execute("SELECT bool_and(revenue_pct IS NULL) FROM mart.q05_category_revenue").fetchone()[0])

    def add_order(order_id, buyer, status="delivered", purchase="2017-01-10 00:00:00"):
        db.execute("INSERT INTO core.fact_order VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
            order_id, "ctx_" + order_id, buyer, status, purchase, purchase,
            "2017-01-12 00:00:00", "2017-01-20 18:00:00", "2017-01-20 00:00:00", "city", "SP"])

    add_order("o1", "b1")
    db.execute("""
      INSERT INTO core.fact_order_item VALUES
        ('o1',1,'p1','s1',10,1,'2017-01-11'), ('o1',2,'p1','s1',20,2,'2017-01-13');
      INSERT INTO core.fact_payment VALUES ('o1',1,10),('o1',2,23);
      INSERT INTO core.fact_review VALUES
        ('shared','o1',5,'title','body','2017-01-21','2017-01-22'),
        ('conflict','o1',1,NULL,'body','2017-01-21','2017-01-22'),
        ('missing','o1',NULL,NULL,NULL,'2017-01-21','2017-01-22');
    """)
    o1 = row("SELECT * FROM mart.v_orders WHERE order_id='o1'")
    check("2 items x 2 payments x 3 reviews remain one order", db.execute("SELECT count(*) FROM mart.v_orders").fetchone()[0] == 1)
    check("independent child totals do not fan out", (o1["item_revenue"], o1["order_gmv"], o1["payment_amount"]) == (30, 33, 33))
    check("source rows vs product/seller groups", (o1["source_rows_count"], o1["units_count"], o1["distinct_product_seller_lines_count"]) == (2, 2, 1))
    check("review pair count independent of payments/items", o1["review_pairs_count"] == 3 and o1["review_avg_pair_score"] == 3)
    check("item mart retains two item keys", db.execute("SELECT count(*) FROM mart.v_order_items").fetchone()[0] == 2)
    check("seller count is distinct order and own units", tuple(row("SELECT orders_delivered,units_delivered,item_revenue FROM mart.q02_sellers_top10").values()) == (1, 2, 30))
    check("empty November survives", tuple(row("SELECT orders_placed,item_revenue FROM mart.q01_revenue_monthly WHERE month_start=DATE '2016-11-01'").values()) == (0, 0))
    check("average is per order, not per item", row("SELECT * FROM mart.q03_average_order")["avg_order_gmv"] == 33)
    late = row("SELECT * FROM mart.v_order_delivery_variants WHERE order_id='o1'")
    check("same day late rules stay distinct", late["is_late_calendar_day"] is False and late["is_late_timestamp"] is True)
    check("min/max deadline rules stay distinct", late["is_handover_after_min_item_deadline"] is True and late["is_handover_after_max_item_deadline"] is False)

    for args in [("o2","b2","delivered","2018-10-01"), ("o3","b3","canceled","2017-01-10"),
                 ("o4","b4","unavailable",None), ("o5","b1"), ("o6","b5"), ("o7","b6"),
                 ("o8","b7"), ("o9","b8"), ("o10","b9"), ("o11","b2")]:
        add_order(*args)
    db.execute("""
      INSERT INTO core.fact_order_item VALUES
        ('o2',1,'p2','s2',10,1,'2017-01-11'), ('o5',1,'p3','s1',0,0,'2017-01-11'),
        ('o6',1,'p1','s1',NULL,2,'2017-01-11'), ('o7',1,'p1','s1',9,NULL,NULL),
        ('o8',1,'p1','s1',NULL,1,'2017-01-11'), ('o8',2,'p1','s1',2,1,NULL),
        ('o9',1,'p1','s1',10,0,'2017-01-11'), ('o10',1,'p1','s1',10,0,'2017-01-11'),
        ('o11',1,'p1','s2',10,0,'2017-01-11');
      INSERT INTO core.fact_payment VALUES
        ('o2',1,11.01), ('o3',1,0), ('o6',1,20), ('o7',1,9), ('o8',1,NULL),
        ('o9',1,10.02), ('o10',1,9.98), ('o11',1,10);
      INSERT INTO core.fact_review VALUES
        ('shared','o2',5,'title','body','2017-01-21','2017-01-22'),
        ('conflict','o2',1,'','body','2017-01-21','2017-01-22');
    """)
    check("all orders survive missing children", db.execute("SELECT count(*) FROM mart.v_orders").fetchone()[0] == 11)
    classes = dict(db.execute("SELECT order_id,payment_coverage FROM mart.v_orders").fetchall())
    check("all four presence classes, zero is present", all(classes[o] == c for o,c in {
        "o1":"both", "o2":"both", "o3":"payments_only", "o4":"neither", "o5":"items_only"}.items()))
    check("missing child money stays NULL with zero count", all(row("SELECT * FROM mart.v_orders WHERE order_id='o4'")[c] is None
          for c in ("order_gmv", "item_revenue", "payment_amount")))
    check("measured zero order GMV is not missing", row("SELECT * FROM mart.v_orders WHERE order_id='o5'")["order_gmv"] == 0)
    incomplete = row("SELECT * FROM mart.v_orders WHERE order_id='o8'")
    check("partial components do not become complete total", incomplete["order_gmv"] is None
          and incomplete["item_revenue"] is None and incomplete["item_revenue_known_sum"] == 2
          and incomplete["price_valid_count"] == 1 and incomplete["source_rows_count"] == 2)
    check("all NULL payments do not become zero", incomplete["payment_amount"] is None
          and incomplete["payment_valid_count"] == 0 and incomplete["payments_count"] == 1)
    check("missing freight preserves known price but not GMV", row("SELECT * FROM mart.v_orders WHERE order_id='o7'")["item_revenue"] == 9
          and row("SELECT * FROM mart.v_orders WHERE order_id='o7'")["order_gmv"] is None)
    noncompare = row("SELECT * FROM mart.v_order_payment_reconciliation WHERE order_id='o6'")
    check("incomplete payment comparator and predicate stay NULL", not noncompare["is_comparable"]
          and noncompare["payment_delta"] is None and noncompare["delta_gt_001"] is None)
    cent = row("SELECT * FROM mart.v_order_payment_reconciliation WHERE order_id='o2'")
    check("exact cent distinct from strict greater-than cent", cent["delta_nonzero_exact"] is True
          and cent["delta_eq_001"] is True and cent["delta_gt_001"] is False)
    totals = row("""SELECT sum(exact_mismatch_orders) AS exact_n, sum(gt_001_mismatch_orders) AS threshold_n,
      sum(exact_signed_delta_sum) AS net, sum(exact_absolute_delta_sum) AS absolute
      FROM mart.v_payment_reconciliation""")
    check("signed/absolute and exact/tolerance use matching sets", totals["exact_n"] == 3
          and totals["threshold_n"] == 2 and abs(float(totals["net"])-.01)<1e-9
          and abs(float(totals["absolute"])-.05)<1e-9)
    check("coverage grid includes all status/classes", db.execute("SELECT count(*) FROM mart.v_payment_reconciliation").fetchone()[0] == 4 * len(statuses))
    check("coverage counts reconcile to orders", db.execute("SELECT sum(orders_count) FROM mart.v_payment_reconciliation").fetchone()[0] == 11)
    q3 = row("SELECT * FROM mart.q03_average_order")
    check("GMV/payment denominators differ independently", q3["n_order_gmv"] == 6 and q3["n_payment_amount"] == 7)
    q4 = row("SELECT * FROM mart.q04_buyers_repeat")
    q4_window = row("SELECT * FROM mart.q04_buyers_repeat_q1_window")
    check("snapshot buyer identity ignores per-order context IDs", q4["buyers"] == 9 and q4["repeat_buyers"] == 2)
    check("window repeat is recomputed within window", q4_window["buyers"] == 8 and q4_window["repeat_buyers"] == 1)
    check("NULL purchase retained in snapshot, excluded by window", q4["unknown_purchase_timestamp_orders"] == 1)
    q5_missing = row("SELECT * FROM mart.q05_category_revenue WHERE category_key='pt:missing'")
    q5_unknown = row("SELECT * FROM mart.q05_category_revenue WHERE category_key='unknown'")
    check("untranslated category distinct from unknown", q5_missing["is_unknown"] is False
          and q5_missing["is_translated"] is False and q5_missing["item_revenue"] == 10
          and q5_unknown["is_unknown"] is True and q5_unknown["item_revenue"] == 0)
    check("incomplete global denominator cannot fabricate shares", q5_missing["total_item_revenue"] is None
          and q5_missing["revenue_pct"] is None)
    check("partial calendar revenue is not zero", row("SELECT * FROM mart.q01_revenue_monthly WHERE month_start=DATE '2017-01-01'")["item_revenue"] is None)
    shared = row("SELECT * FROM mart.v_review WHERE review_id='shared'")
    conflict = row("SELECT * FROM mart.v_review WHERE review_id='conflict'")
    check("shared review keeps all associations with one payload", shared["association_count"] == 2
          and shared["payload_variant_count"] == 1 and shared["review_score"] == 5)
    check("NULL-vs-empty payload conflict is not arbitrarily resolved", conflict["payload_variant_count"] == 2
          and conflict["has_payload_conflict"] is True and all(conflict[c] is None for c in (
              "review_score", "review_comment_title", "review_comment_message", "review_creation_date", "review_answer_timestamp")))
    check("conflicting variants remain available", db.execute("SELECT sum(variant_association_count) FROM mart.v_review_payload_variants WHERE review_id='conflict'").fetchone()[0] == 2)
    weights = {r["weight_basis"]:r for r in [row("SELECT * FROM mart.v_review_weighting WHERE weight_basis=?", [w])
        for w in ("review_order_pair", "review_id_unambiguous_payload", "order_mean_of_review_pairs")]}
    check("pair/ID/order review units remain different", weights["review_order_pair"]["denominator"] == 4
          and weights["review_id_unambiguous_payload"]["denominator"] == 1
          and weights["order_mean_of_review_pairs"]["denominator"] == 2)
    check("ID conflicts and missing score visibly excluded", weights["review_id_unambiguous_payload"]["excluded_units"] == 2)
    check("missing item deadline makes both handover variants unknown", all(
          row("SELECT * FROM mart.v_order_delivery_variants WHERE order_id='o8'")[c] is None
          for c in ("is_handover_after_min_item_deadline", "is_handover_after_max_item_deadline")))
    # Break only purchase->carrier chronology; delivery-vs-promise stays usable.
    db.execute("UPDATE core.fact_order SET order_delivered_carrier_date=TIMESTAMP '2017-01-01' WHERE order_id='o1'")
    late = row("SELECT * FROM mart.v_order_delivery_variants WHERE order_id='o1'")
    check("chronology exclusion is specific to affected interval", late["purchase_to_carrier_days"] is None
          and late["purchase_to_delivery_days"] is not None and late["is_late_timestamp"] is True)
    db.execute("INSERT INTO core.fact_payment VALUES ('o8',2,5)")
    partial_payment = row("SELECT * FROM mart.v_orders WHERE order_id='o8'")
    check("partial payments retain known subtotal and unknown full amount", partial_payment["payment_amount"] is None
          and partial_payment["payment_known_sum"] == 5 and partial_payment["payment_valid_count"] == 1
          and partial_payment["payments_count"] == 2)
    db.execute("UPDATE core.fact_payment SET payment_value=10.0101 WHERE order_id='o11'")
    precision = row("SELECT * FROM mart.v_order_payment_reconciliation WHERE order_id='o11'")
    check("tolerance compares exact source precision before display rounding", abs(float(precision["payment_delta"])-.0101)<1e-9
          and precision["delta_gt_001"] is True and precision["delta_eq_001"] is False)
    # Parse/bind the SQL control body separately from psql-only guards. Execute
    # no real-data oracle against the synthetic data as if it were a DB PASS.
    control = (ROOT / "answers/control.sql").read_text()
    oracle = control[control.index("CREATE TEMP VIEW w10_control_results AS"):control.index("TABLE w10_control_results;")]
    db.execute(oracle)
    check("pinned control body parses/binds", db.execute("SELECT count(*) FROM w10_control_results").fetchone()[0] == 42)
    check("real-data controls reject synthetic input", db.execute("SELECT bool_and(ok) FROM w10_control_results").fetchone()[0] is False)
    for wrapper in sorted((ROOT / "answers").glob("*.sql")):
        if wrapper.name == "control.sql":
            continue  # psql meta-commands and pinned real-data oracle, not fixture.
        db.execute(wrapper.read_text()).fetchall()
        checks.append("wrapper binds: " + wrapper.name)
    db.close()
    return {
        "status": "offline_only",
        "engine": "DuckDB " + duckdb.__version__,
        "postgresql_executed": False,
        "core_builder_executed": False,
        "olist_csv_or_raw_read": False,
        "parsed_statement_counts": parsed_counts,
        "checks_passed": len(checks),
        "checks": checks,
        "limits": ["Not PostgreSQL parsing/runtime", "Synthetic interface fixture only",
                   "No real core answers, DB controls, rollback or rebuild evidence"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run()
    inputs = [*SQL_PATHS, "model/CONTRACT.md", "docs/metric-definitions.md", "answers/check_offline.py", "answers/baseline-manifest.json"]
    inputs.extend(str(p.relative_to(ROOT)) for p in sorted((ROOT / "answers").glob("*.sql")))
    report["checked_file_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs}
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "engine", "checks_passed", "postgresql_executed")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
