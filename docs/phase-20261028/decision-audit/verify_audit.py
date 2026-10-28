#!/usr/bin/env python3
"""Small read-only audit: pinned sources, published evidence, selected CSV claims.

No SQL/model execution, server, dependency install or full fixture. Outputs only
inside decision-audit/evidence. Existing experiment outputs are never rewritten.
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWN = Path(__file__).resolve().parent
BASE = "aab62d7a59f196be051df12466fb21c0da4659b9"
MAIN = "6452806eae21d13126da9de8ebaba01a2152eaea"
EXPS = Path("docs/phase-20261028/experiments")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def load_exp(name):
    return json.loads((ROOT / EXPS / name / "results.json").read_text())


def run(csv_dir):
    sources = ["AGENTS.md", "docs/workstreams.md", "docs/decision-log.md",
               "docs/ideas.md", "research/README.md", "docs/idea-synthesis.md",
               "docs/implementation-brief-20261028.md", "docs/metric-definitions.md",
               "hack-context/hackathon-students/docs/tasks.md",
               "hack-context/hackathon-students/docs/handout.md",
               "model/10_dims.sql", "model/20_facts.sql", "model/40_mart.sql",
               "model/50_answers.sql", "model/55_answers_block_b.sql",
               "answers/q06-q10/q07.sql", "answers/q06-q10/q10.sql",
               "docs/phase-20261028/README.md", "docs/phase-20261028/index.html",
               "docs/phase-20261028/FRONTEND-HANDOFF.md",
               "docs/phase-20261028/evidence/pg16-small-02/summary.json"]
    for name in ["delivery-data", "review-data", "payments-prices", "category-history"]:
        sources.extend(str(EXPS / name / f) for f in ["report.md", "script.py", "results.json"])
    sources.append(str(EXPS / "category-history/tasks.source.md"))
    manifest = {}
    for path in sources:
        blob = git("show", f"{BASE}:{path}")
        assert (ROOT / path).read_bytes() == blob, f"Source drift: {path}"
        manifest[path] = {"sha256": digest(blob), "git_blob": git("rev-parse", f"{BASE}:{path}").decode().strip()}
    tasks = (ROOT / EXPS / "category-history/tasks.source.md").read_bytes()
    assert digest(tasks) == "c24f3190729a672c09fcb97854a678fa02712456350038ff2bd738095652d1c5"
    assert tasks == (ROOT / "hack-context/hackathon-students/docs/tasks.md").read_bytes()
    synthesis = (ROOT / "docs/idea-synthesis.md").read_text().split("## 9.", 1)[1].split("## Решение", 1)[0]
    rows = re.findall(r"^\| (\d+) \| (.*?) \|", synthesis, re.M)
    assert [int(n) for n, _ in rows] == list(range(1, 18))
    ledger = (ROOT / "docs/decision-log.md").read_text()
    u15 = ledger.split("## U-15", 1)[1].split("## U-16", 1)[0]
    assert "accepted_decision" in u15 and "Остаётся открытым" in u15
    small_pg = json.loads((ROOT / "docs/phase-20261028/evidence/pg16-small-02/summary.json").read_text())
    pg_bindings = {}
    for path, expected in small_pg["files_sha256"].items():
        actual = digest((ROOT / path).read_bytes())
        pg_bindings[path] = {"matches_published_execution": actual == expected, "sha256": actual}
        assert actual == expected, path
    assert small_pg["full_olist"] == "not_run" and small_pg["csv_raw_equality"] == "not_run"

    review, delivery, category = [load_exp(n) for n in ["review-data", "delivery-data", "category-history"]]
    # Arithmetic over existing published evidence, not another model run.
    for policy in review["results"].values():
        assert all(policy[str(i)]["mean_days"] > policy[str(i + 1)]["mean_days"] for i in range(1, 5))
    within = sum(v["orders_count"] for v in review["results"]["within_score"].values())
    single = sum(v["orders_count"] for v in review["results"]["single_score_only"].values())
    assert (within, single) == (96021, 95643)
    sets = list(delivery["threshold_500_state_sets"].values())
    assert len(sets[0]) == 17 and all(v == sets[0] for v in sets)
    assert category["simulation"]["passed"] == 19

    # Tiny logical counterexamples. These distinguish contracts, not quality.
    examples = {
        "threshold": {"all_orders": 500, "delivered": 499, "all_qualifies": 500 >= 500, "delivered_qualifies": 499 >= 500},
        "deadline": {"deadlines": [10, 20], "carrier": 15, "after_min": 15 > 10, "after_max": 15 > 20},
        "rating_units": {"order_A_scores": [1, 1], "order_B_scores": [5], "pair_mean": 7 / 3, "order_mean": 3},
        "stable_ranking_different_estimands": {"policy_A": [21.307, 16.652, 14.261, 12.310, 10.685], "policy_B": [21.340, 16.648, 14.244, 12.304, 10.679]},
        "history_conflict": {"product_category": "C", "seller_category": "B", "both_stored": True, "effective_category_requires_precedence": True},
    }
    assert examples["threshold"]["all_qualifies"] != examples["threshold"]["delivered_qualifies"]
    assert examples["deadline"]["after_min"] != examples["deadline"]["after_max"]
    assert examples["rating_units"]["pair_mean"] != examples["rating_units"]["order_mean"]

    # A compact targeted CSV recheck; reads four existing files, retains only
    # order status/date and score sets. Does not reconstruct raw/core or all marts.
    def records(name):
        with (csv_dir / name).open(newline="", encoding="utf-8") as f:
            yield from csv.DictReader(f)

    names = ["olist_orders_dataset.csv", "olist_order_reviews_dataset.csv",
             "olist_order_items_dataset.csv", "olist_order_payments_dataset.csv"]
    hashes = {name: digest((csv_dir / name).read_bytes()) for name in names}
    statuses, years, counts, day_late, timestamp_late = {}, {}, Counter(), 0, 0
    target = None
    for row in records(names[0]):
        oid, status = row["order_id"], row["order_status"]
        statuses[oid], years[oid] = status, row["order_purchase_timestamp"][:4]
        counts[status] += 1
        if status == "delivered" and row["order_delivered_customer_date"] and row["order_estimated_delivery_date"]:
            d, e = row["order_delivered_customer_date"], row["order_estimated_delivery_date"]
            day_late += d[:10] > e[:10]
            timestamp_late += d > e
        if oid == "8563039e855156e48fccee4d611a3196":
            target = {k: row[k] for k in ["order_id", "order_status", "order_estimated_delivery_date", "order_delivered_customer_date"]}
    score_sets = defaultdict(set)
    for row in records(names[1]):
        if statuses[row["order_id"]] == "delivered" and row["review_score"]:
            score_sets[row["order_id"]].add(int(row["review_score"]))
    price_counts, price_sets = Counter(), defaultdict(set)
    for row in records(names[2]):
        if row["product_id"] == "437c05a395e9e47f9762e677a7068ce7":
            status = statuses[row["order_id"]]
            price_counts[status] += 1
            price_sets[status].add(row["price"])
    payment_counts = Counter()
    for row in records(names[3]):
        oid = row["order_id"]
        if years[oid] == "2018":
            payment_counts["all_2018"] += 1
            if statuses[oid] == "delivered":
                payment_counts["delivered_2018"] += 1
    observed = {"statuses": dict(counts), "delivered_late_day": day_late,
                "delivered_late_timestamp": timestamp_late,
                "review_scored_delivered": len(score_sets),
                "review_conflicting_delivered": sum(len(v) > 1 for v in score_sets.values()),
                "review_within_score_memberships": sum(len(v) for v in score_sets.values()),
                "review_single_score_orders": sum(len(v) == 1 for v in score_sets.values()),
                "q6_leader_units_by_status": dict(price_counts),
                "q6_leader_known_prices_all": len(set.union(*price_sets.values())),
                "q6_leader_known_prices_delivered": len(price_sets["delivered"]),
                "payments": dict(payment_counts), "same_day_example": target}
    assert sum(counts.values()) == 99441 and counts["delivered"] == 96478
    assert (day_late, timestamp_late) == (6534, 7826)
    assert (len(score_sets), observed["review_conflicting_delivered"], observed["review_within_score_memberships"], observed["review_single_score_orders"]) == (95832, 189, within, single)
    assert (price_counts["delivered"], price_counts["shipped"]) == (151, 4)
    assert observed["q6_leader_known_prices_all"] == observed["q6_leader_known_prices_delivered"] == 31
    assert (payment_counts["all_2018"], payment_counts["delivered_2018"]) == (56015, 54748)
    for name, expected in review["inputs_sha256"].items():
        assert hashes[Path(name).name] == expected
    prices_payments = load_exp("payments-prices")
    for name, expected in prices_payments["input_baseline"]["files"].items():
        if name in hashes:
            assert hashes[name] == expected["sha256"], name
    assert all(digest((csv_dir / n).read_bytes()) == h for n, h in hashes.items())

    ui = git("show", f"{MAIN}:app/web/src/pages/AnswersB.tsx")
    ui_lines = ui.decode().splitlines()
    defaults = {str(i): line.strip() for i, line in enumerate(ui_lines, 1) if "useViewParam<" in line}
    out = {"at_utc": datetime.now(timezone.utc).isoformat(), "input_sha": BASE,
           "method": "static pinned-source audit + existing execution readback + targeted streaming CSV + tiny arithmetic examples",
           "not_run": ["new model/SQL runs", "database access", "full lifecycle", "UI/browser", "benchmark"],
           "sources": manifest, "original_17": rows, "u15": u15.strip(),
           "pg16_existing_execution_hash_binding": pg_bindings,
           "existing_pg16_scope": small_pg["scope_note"],
           "csv_hashes_before_equal_after": hashes, "csv_targeted_observations": observed,
           "synthetic_examples": examples,
           "supplemental_ui": {"commit": MAIN, "sha256": digest(ui), "defaults_by_line": defaults,
                               "scope": "source only; no browser or E2E claim"},
           "status": "pass"}
    output = OWN / "evidence/checks.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "pass", "evidence": str(output.relative_to(ROOT)), "source_files": len(manifest), "original_forks": len(rows), "csv_files": len(names)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv-dir", type=Path, required=True)
    run(parser.parse_args().csv_dir)
