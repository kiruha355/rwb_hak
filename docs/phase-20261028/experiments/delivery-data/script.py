#!/usr/bin/env python3
"""Offline CSV sensitivity oracle for Q7/Q10; no DB, downloads or third parties.

Run from anywhere: python3 <repo>/docs/phase-20261028/experiments/delivery-data/script.py
Only results.json beside this script is written. Lookups contain IDs/state/score
bitmasks; each CSV is otherwise processed one record at a time. Exact integer
seconds are accumulated; rounding occurs only for JSON presentation.
"""
import csv
import hashlib
import itertools
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MAIN = "bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4"
CANDIDATE = "99bcbb366720f912ef6017a40aa5dbd6a671a8a4"
INTEGRATION = "b0bd0200a0a88b6bb7eb242cfc11d3239ff0fb68"
REQUIREMENTS = "558f0f6a38110acc9fcf4386a7e53ece973aedf5"
TASKS_SHA256 = "c24f3190729a672c09fcb97854a678fa02712456350038ff2bd738095652d1c5"
EXAMPLE = "8563039e855156e48fccee4d611a3196"
DATE_COLS = {
    "P": "order_purchase_timestamp", "A": "order_approved_at",
    "C": "order_delivered_carrier_date", "D": "order_delivered_customer_date",
    "E": "order_estimated_delivery_date",
}
PAIRS = {"purchase_to_delivery": ("P", "D"),
         "purchase_to_carrier": ("P", "C"),
         "carrier_to_delivery": ("C", "D")}
CHRONOLOGY = [("P", "A"), ("P", "C"), ("P", "D"),
              ("A", "C"), ("A", "D"), ("C", "D"), ("P", "E")]
# Numeric reference extracted from the hash-verified historical audit results.
# That JSON is not published in MAIN; do not depend on its local presence.
REFERENCE_STATUSES = {"approved": 2, "canceled": 625, "created": 5,
    "delivered": 96478, "invoiced": 314, "processing": 301,
    "shipped": 1107, "unavailable": 609}
REFERENCE_MISSING = {"approved": (0, 0, 2, 2, 0),
    "canceled": (0, 141, 550, 619, 0), "created": (0, 5, 5, 5, 0),
    "delivered": (0, 14, 2, 8, 0), "invoiced": (0, 0, 314, 314, 0),
    "processing": (0, 0, 301, 301, 0), "shipped": (0, 0, 0, 1107, 0),
    "unavailable": (0, 0, 609, 609, 0)}  # missing P/A/C/D/E
REFERENCE_CHRONOLOGY = {"A_before_P": (0, 99281), "C_before_P": (166, 97658),
    "D_before_P": (0, 96476), "C_before_A": (1359, 97644),
    "D_before_A": (61, 96462), "D_before_C": (23, 96475),
    "E_before_P": (0, 99441)}  # anomalies, comparable pairs


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def blob(ref, path):
    return git("show", ref + ":" + path)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def filehash(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with (ROOT / path).open(newline="", encoding="utf-8-sig") as f:
        yield from csv.DictReader(f)


def pct(n, d):
    return round(100 * n / d, 9) if d else None


def independent_totals(path):
    """Second pass: direct string date comparisons; separate duration parser."""
    c = Counter()
    for row in rows(path):
        c["all_orders"] += 1
        if row["order_status"] != "delivered":
            continue
        c["delivered"] += 1
        p = row["order_purchase_timestamp"]
        d = row["order_delivered_customer_date"]
        e = row["order_estimated_delivery_date"]
        carrier = row["order_delivered_carrier_date"]
        if d and e:
            c["late_denominator"] += 1
            c["late_day"] += d[:10] > e[:10]
            c["late_timestamp"] += d > e
            c["same_promised_date"] += d[:10] == e[:10]
        if p and d:
            start = datetime.strptime(p, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
            sec = int((end - start).total_seconds())
            if sec >= 0:
                c["purchase_duration_n"] += 1
                c["purchase_duration_sum_seconds"] += sec
        if carrier and d:
            start = datetime.strptime(carrier, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
            sec = int((end - start).total_seconds())
            if sec >= 0:
                c["carrier_duration_n"] += 1
                c["carrier_duration_sum_seconds"] += sec
            else:
                c["carrier_negative_n"] += 1
    return dict(c)


class Aggregate:
    def __init__(self):
        self.n = 0
        self.seconds = Counter()
        self.valid = Counter()
        self.raw_seconds = Counter()
        self.raw_n = Counter()
        self.negative = Counter()
        self.days = Counter()
        self.floors = Counter()
        self.late_n = 0
        self.day_late = 0
        self.ts_late = 0
        self.same_day = 0
        self.common_n = 0
        self.common_p = 0
        self.common_c = 0
        self.common_handover = 0

    def add(self, dates, eligible):
        self.n += 1
        if not eligible:
            return
        observed = {}
        for name, (start, end) in PAIRS.items():
            if dates[start] is None or dates[end] is None:
                continue
            seconds = int((dates[end] - dates[start]).total_seconds())
            self.raw_n[name] += 1
            self.raw_seconds[name] += seconds
            if seconds < 0:
                self.negative[name] += 1
                continue
            observed[name] = seconds
            self.valid[name] += 1
            self.seconds[name] += seconds
            self.days[name] += (dates[end].date() - dates[start].date()).days
            self.floors[name] += seconds // 86400
        if "purchase_to_delivery" in observed and "carrier_to_delivery" in observed:
            self.common_n += 1
            self.common_p += observed["purchase_to_delivery"]
            self.common_c += observed["carrier_to_delivery"]
            self.common_handover += observed["purchase_to_delivery"] - observed["carrier_to_delivery"]
        if dates["D"] is not None and dates["E"] is not None:
            self.late_n += 1
            self.day_late += dates["D"].date() > dates["E"].date()
            self.ts_late += dates["D"] > dates["E"]
            self.same_day += dates["D"].date() == dates["E"].date()

    def result(self):
        durations = {}
        for name in PAIRS:
            n, raw_n = self.valid[name], self.raw_n[name]
            durations[name] = {
                "denominator": n, "unknown_or_ineligible": self.n - n,
                "sum_seconds": self.seconds[name],
                "mean_elapsed_days": round(self.seconds[name] / n / 86400, 12) if n else None,
                "mean_calendar_date_difference_days": round(self.days[name] / n, 12) if n else None,
                "mean_floored_elapsed_days": round(self.floors[name] / n, 12) if n else None,
                "raw_observed_pairs": raw_n, "negative_intervals": self.negative[name],
                "naive_signed_mean_days": round(self.raw_seconds[name] / raw_n / 86400, 12) if raw_n else None,
                "naive_zero_filled_mean_days": round(self.seconds[name] / self.n / 86400, 12) if self.n else None,
            }
        return {
            "orders_count": self.n, "durations": durations,
            "lateness": {
                "denominator": self.late_n, "unknown_or_ineligible": self.n - self.late_n,
                "calendar_day_late_orders": self.day_late,
                "timestamp_late_orders": self.ts_late,
                "same_promised_calendar_date": self.same_day,
                "calendar_day_late_pct": pct(self.day_late, self.late_n),
                "timestamp_late_pct": pct(self.ts_late, self.late_n),
                "delta_percentage_points": pct(self.ts_late - self.day_late, self.late_n),
                "calendar_unknown_bounds_pct": [pct(self.day_late, self.n),
                    pct(self.day_late + self.n - self.late_n, self.n)],
                "timestamp_unknown_bounds_pct": [pct(self.ts_late, self.n),
                    pct(self.ts_late + self.n - self.late_n, self.n)],
            },
            "common_purchase_carrier_cohort": {
                "denominator": self.common_n,
                "purchase_mean_days": round(self.common_p / self.common_n / 86400, 12) if self.common_n else None,
                "carrier_mean_days": round(self.common_c / self.common_n / 86400, 12) if self.common_n else None,
                "handover_difference_mean_days": round(self.common_handover / self.common_n / 86400, 12) if self.common_n else None,
            },
        }


def main():
    started = datetime.now(timezone.utc).isoformat()
    baseline_path = "research/data-audit-2026-10-28/manifest.json"
    baseline_bytes = blob(MAIN, baseline_path)
    baseline = json.loads(baseline_bytes)
    by_path = {r["path"]: r for r in baseline["files"]}
    input_paths = ["data/olist_orders_dataset.csv", "data/olist_customers_dataset.csv",
                   "data/olist_order_reviews_dataset.csv"]
    inputs = []
    for path in input_paths:
        actual = filehash(ROOT / path)
        expected = by_path[path]["sha256"]
        assert actual == expected, (path, actual, expected)
        inputs.append({"path": path, "bytes": (ROOT / path).stat().st_size,
                       "sha256": actual, "baseline_sha256": expected, "matches_baseline": True})
    tasks = blob(INTEGRATION, "hack-context/hackathon-students/docs/tasks.md")
    assert digest(tasks) == TASKS_SHA256
    evidence_blobs = []
    for ref, path in [(MAIN, baseline_path),
                      (MAIN, "model/40_mart.sql"),
                      (CANDIDATE, "answers/q06-q10/q07.sql"),
                      (CANDIDATE, "answers/q06-q10/q10.sql"),
                      (INTEGRATION, "model/40_mart.sql"),
                      (INTEGRATION, "model/55_answers_block_b.sql"),
                      (INTEGRATION, "hack-context/hackathon-students/docs/tasks.md")]:
        data = blob(ref, path)
        evidence_blobs.append({"ref": ref, "path": path, "sha256": digest(data), "bytes": len(data)})

    customers = {}
    for row in rows(input_paths[1]):
        assert row["customer_id"] not in customers
        customers[row["customer_id"]] = row["customer_state"] or None
    score_masks = {}
    review_rows = Counter()
    review_n = null_score_n = 0
    for row in rows(input_paths[2]):
        review_n += 1
        oid = row["order_id"]
        review_rows[oid] += 1
        if row["review_score"]:
            score = int(row["review_score"])
            assert 1 <= score <= 5, "Out-of-range score requires an explicit policy"
            score_masks[oid] = score_masks.get(oid, 0) | (1 << score)
        else:
            null_score_n += 1

    populations = defaultdict(Aggregate)
    state_groups = defaultdict(Aggregate)
    score_groups = defaultdict(Aggregate)
    status_counts = Counter()
    missing_dates = defaultdict(Counter)
    date_masks = Counter()
    anomalies_matrix = Counter()
    anomaly_counts = Counter()
    anomaly_pairs = Counter()
    status_intervals = defaultdict(Aggregate)
    estimate_times = Counter()
    review_coverage = defaultdict(Counter)
    differing = defaultdict(list)
    examples = {}
    seen = set()
    unjoined = Counter()
    same_day_seconds = Counter()
    timestamp_only_by_state = defaultdict(list)
    strict_policy = defaultdict(Aggregate)
    for record, row in enumerate(rows(input_paths[0]), start=1):
        oid, status = row["order_id"], row["order_status"]
        assert oid not in seen
        seen.add(oid)
        delivered = status == "delivered"
        state = customers.get(row["customer_id"])
        if row["customer_id"] not in customers:
            unjoined["orders_without_customer"] += 1
        if not state:
            unjoined["orders_without_state"] += 1
        dates = {k: datetime.fromisoformat(row[c]) if row[c] else None for k, c in DATE_COLS.items()}
        status_counts[status] += 1
        missing_dates[status]["orders"] += 1
        for k, column in DATE_COLS.items():
            missing_dates[status][column] += dates[k] is None
        mask = "".join(k if dates[k] else "-" for k in DATE_COLS)
        date_masks[(status, mask)] += 1
        anomalies = []
        for start, end in CHRONOLOGY:
            name = f"{end}_before_{start}"
            if dates[start] is not None and dates[end] is not None:
                anomaly_pairs[(status, name)] += 1
                if dates[end] < dates[start]:
                    anomalies.append(name)
                    anomaly_counts[(status, name)] += 1
                    differing[name].append(oid)
        anomalies_matrix[(status, mask, ",".join(anomalies) or "none")] += 1
        if dates["E"] is not None:
            estimate_times[dates["E"].time().isoformat()] += 1
        status_intervals[status].add(dates, True)
        populations["all_statuses_candidate"].add(dates, delivered)
        populations["any_status_with_delivery_evidence"].add(dates, True)
        state_groups[(state, "all_statuses")].add(dates, delivered)
        if delivered:
            populations["delivered"].add(dates, True)
            state_groups[(state, "delivered")].add(dates, True)
            strict_policy["metric_specific"].add(dates, True)
            if not anomalies:
                strict_policy["drop_any_chronology_anomaly"].add(dates, True)
            else:
                differing["delivered_with_any_chronology_anomaly"].append(oid)
            if dates["D"] is None or dates["P"] is None:
                differing["delivered_missing_purchase_or_delivery"].append(oid)
            if dates["C"] is None:
                differing["delivered_missing_carrier"].append(oid)
            if dates["C"] and dates["D"] and dates["D"] < dates["C"]:
                differing["delivered_negative_carrier_duration"].append(oid)
            if dates["D"] and dates["E"] and dates["D"].date() == dates["E"].date():
                differing["delivered_on_promised_calendar_date"].append(oid)
                if dates["D"] > dates["E"]:
                    differing["delivered_late_timestamp_only"].append(oid)
                    timestamp_only_by_state[state].append(oid)
                    same_day_seconds[int((dates["D"] - dates["E"]).total_seconds())] += 1
        else:
            differing["non_delivered_orders"].append(oid)
            if dates["D"] is not None:
                differing["non_delivered_with_delivery_date"].append(oid)

        mask_scores = score_masks.get(oid, 0)
        scores = [s for s in range(1, 6) if mask_scores & (1 << s)]
        for pop in ["all_statuses"] + (["delivered"] if delivered else []):
            coverage = review_coverage[pop]
            coverage["orders"] += 1
            coverage["no_valid_score"] += not scores
            coverage["multiple_distinct_scores"] += len(scores) > 1
            coverage["multiple_review_rows"] += review_rows.get(oid, 0) > 1
            for policy in ["within_score"] + (["single_score_only"] if len(scores) == 1 else []):
                for score in scores:
                    score_groups[(pop, policy, score)].add(dates, delivered)
        tags = []
        if oid == EXAMPLE:
            tags.append("requested_real_example")
        if delivered and dates["D"] is None:
            tags.append("missing_delivered_date")
        if delivered and dates["D"] and dates["C"] and dates["D"] < dates["C"]:
            tags.append("negative_carrier_duration")
        if delivered and dates["C"] and dates["P"] and dates["C"] < dates["P"]:
            tags.append("carrier_before_purchase")
        if not delivered and dates["D"]:
            tags.append("non_delivered_with_delivery_date")
        for tag in tags:
            if tag not in examples or oid < examples[tag]["order_id"] or tag == "requested_real_example":
                one = Aggregate()
                one.add(dates, True)
                examples[tag] = {"order_id": oid, "orders_csv_record": record,
                    "orders_csv_physical_line": record + 1, "customer_state": state,
                    "raw_fields": row, "known_scores": scores,
                    "anomalies": anomalies, "observed_metrics": one.result()}
    assert not set(score_masks).difference(seen), "Dangling review order"
    for inp in inputs:
        assert filehash(ROOT / inp["path"]) == inp["sha256"], "Input changed during streaming pass"
    baseline_results_path = "research/data-audit-2026-10-28/results.json"
    declared = next(x["sha256"] for x in baseline["artifact_hashes"] if x["path"] == baseline_results_path)
    assert declared == "58badd61e5b639d89e7fc2daf26125c46f20e409cac397cdccafabaf6b1113c8"
    assert dict(status_counts) == REFERENCE_STATUSES
    for status, missing in REFERENCE_MISSING.items():
        assert tuple(missing_dates[status][c] for c in DATE_COLS.values()) == missing
    comparisons = []
    for start, end in CHRONOLOGY:
        name = f"{end}_before_{start}"
        baseline_name = DATE_COLS[end] + "_before_" + DATE_COLS[start]
        expected_count, expected_comparable = REFERENCE_CHRONOLOGY[name]
        actual = len(differing[name])
        comparable = sum(v for (s, a), v in anomaly_pairs.items() if a == name)
        assert actual == expected_count and comparable == expected_comparable
        comparisons.append({"comparison": baseline_name, "count": actual,
                            "comparable": comparable, "matches_numeric_baseline": True})

    states = []
    for state in sorted({key[0] for key in state_groups}, key=lambda x: x or ""):
        a = state_groups[(state, "all_statuses")].result()
        d = state_groups[(state, "delivered")].result()
        counts = {"all_orders": a["orders_count"], "delivered_orders": d["orders_count"],
            "duration_measurable": d["durations"]["purchase_to_delivery"]["denominator"],
            "late_measurable": d["lateness"]["denominator"],
            "carrier_duration_measurable": d["durations"]["carrier_to_delivery"]["denominator"]}
        states.append({"state": state, "threshold_counts": counts,
            "passes_500": {k: n >= 500 for k, n in counts.items()},
            "all_statuses": a, "delivered": d})
    threshold_sets = {k: [r["state"] for r in states if r["passes_500"][k]]
                      for k in states[0]["passes_500"]}
    qualifying = [r for r in states if r["passes_500"]["delivered_orders"]]
    rank_keys = {
        "purchase_to_delivery": lambda r: r["delivered"]["durations"]["purchase_to_delivery"]["mean_elapsed_days"],
        "carrier_to_delivery": lambda r: r["delivered"]["durations"]["carrier_to_delivery"]["mean_elapsed_days"],
        "purchase_common_cohort": lambda r: r["delivered"]["common_purchase_carrier_cohort"]["purchase_mean_days"],
        "carrier_common_cohort": lambda r: r["delivered"]["common_purchase_carrier_cohort"]["carrier_mean_days"],
        "late_calendar_day": lambda r: r["delivered"]["lateness"]["calendar_day_late_pct"],
        "late_timestamp": lambda r: r["delivered"]["lateness"]["timestamp_late_pct"],
    }
    rankings = {name: [r["state"] for r in sorted(qualifying, key=lambda r: (-key(r), r["state"] or ""))]
                for name, key in rank_keys.items()}
    inversions = {}
    for first, second in [("purchase_to_delivery", "carrier_to_delivery"),
                          ("purchase_common_cohort", "carrier_common_cohort"),
                          ("late_calendar_day", "late_timestamp")]:
        key_a, key_b = rank_keys[first], rank_keys[second]
        pairs = []
        for x, y in itertools.combinations(qualifying, 2):
            if (key_a(x) - key_a(y)) * (key_b(x) - key_b(y)) < 0:
                pairs.append([x["state"], y["state"]])
        inversions[first + "_versus_" + second] = {"possible_pairs": len(qualifying) * (len(qualifying)-1)//2,
                                                   "inverted_pairs": len(pairs), "pairs": pairs}
    q10 = []
    for pop in ["all_statuses", "delivered"]:
        for policy in ["within_score", "single_score_only"]:
            for score in range(1, 6):
                q10.append({"population": pop, "score_policy": policy, "score": score,
                            **score_groups[(pop, policy, score)].result()})

    # Small arithmetic counterexamples, explicitly not observations in the CSV.
    synthetic_thresholds = [
        {"scenario": "500 delivered, one missing delivery date", "all_orders": 500,
         "delivered_orders": 500, "duration_measurable": 499},
        {"scenario": "500 orders, one shipped", "all_orders": 500,
         "delivered_orders": 499, "duration_measurable": 499},
    ]
    for case in synthetic_thresholds:
        case["passes_500"] = {k: case[k] >= 500 for k in
                              ["all_orders", "delivered_orders", "duration_measurable"]}
        assert len(set(case["passes_500"].values())) == 2
    reference = independent_totals(input_paths[0])
    delivered_results = populations["delivered"].result()
    expected_reference = {
        "all_orders": len(seen), "delivered": delivered_results["orders_count"],
        "late_denominator": delivered_results["lateness"]["denominator"],
        "late_day": delivered_results["lateness"]["calendar_day_late_orders"],
        "late_timestamp": delivered_results["lateness"]["timestamp_late_orders"],
        "same_promised_date": delivered_results["lateness"]["same_promised_calendar_date"],
        "purchase_duration_n": delivered_results["durations"]["purchase_to_delivery"]["denominator"],
        "purchase_duration_sum_seconds": delivered_results["durations"]["purchase_to_delivery"]["sum_seconds"],
        "carrier_duration_n": delivered_results["durations"]["carrier_to_delivery"]["denominator"],
        "carrier_duration_sum_seconds": delivered_results["durations"]["carrier_to_delivery"]["sum_seconds"],
        "carrier_negative_n": delivered_results["durations"]["carrier_to_delivery"]["negative_intervals"],
    }
    assert reference == expected_reference, (reference, expected_reference)
    for inp in inputs:
        assert filehash(ROOT / inp["path"]) == inp["sha256"], "Input changed during second pass"
    robust_scores = []
    for policy in ["within_score", "single_score_only"]:
        groups = [x for x in q10 if x["population"] == "delivered" and x["score_policy"] == policy]
        for measure in ["purchase_to_delivery", "carrier_to_delivery", "late_calendar_day", "late_timestamp"]:
            values = [x["durations"][measure]["mean_elapsed_days"] if measure in PAIRS else
                      x["lateness"]["calendar_day_late_pct" if measure == "late_calendar_day" else "timestamp_late_pct"]
                      for x in groups]
            monotone = all(x > y for x, y in zip(values, values[1:]))
            assert monotone
            robust_scores.append({"policy": policy, "measure": measure,
                                  "strictly_decreases_from_score_1_to_5": monotone})
    result = {
        "kind": "streaming_csv_sensitivity_oracle_not_core_answers", "database_accessed": False,
        "generated_by": "Codex / Sol; AI-produced script and interpretation, verified by assertions and independent small pass",
        "started_utc": started, "completed_utc": datetime.now(timezone.utc).isoformat(),
        "source_bindings": {"head": git("rev-parse", "HEAD").decode().strip(),
            "main": MAIN, "candidate": CANDIDATE, "integration": INTEGRATION,
            "requirements_commit": REQUIREMENTS, "requirements_sha256": digest(tasks),
            "requirements_url": f"https://github.com/daniilivanovp-droid/hackathon-students/blob/{REQUIREMENTS}/docs/tasks.md",
            "requirements_upstream_byte_equality_verified_before_run": True,
            "baseline_manifest_sha256": digest(baseline_bytes),
            "baseline_numeric_results_sha256": declared,
            "numeric_baseline_mode": "embedded reference extracted from hash-verified historical results; unpublished local JSON not required",
            "script_sha256": filehash(Path(__file__)), "inputs": inputs,
            "git_blobs": evidence_blobs},
        "checks": {"three_used_csv_hashes_match_published_baseline": True,
            "inputs_unchanged_during_pass": True,
            "status_and_missing_date_numeric_baseline_equal": True,
            "chronology_numeric_baseline_equal": comparisons,
            "customer_ids_unique": True, "order_ids_unique": True,
            "review_scores_1_to_5": True, "review_orders_all_present": True,
            "customers": len(customers), "orders": len(seen), "review_rows": review_n,
            "review_rows_without_score": null_score_n, "join_gaps": dict(unjoined)},
        "independent_second_pass": {"method": "lexical ISO-date/timestamp comparison plus datetime.strptime duration parser",
                                    "equal_to_first_pass": True, "totals": reference},
        "q10_robustness_checks": robust_scores,
        "date_mask_legend": DATE_COLS,
        "statuses": dict(sorted(status_counts.items())),
        "missing_dates_by_status": {s: dict(c) for s, c in sorted(missing_dates.items())},
        "status_date_presence_matrix": [{"status": s, "mask": m, "orders": n}
            for (s, m), n in sorted(date_masks.items())],
        "status_date_presence_anomalies_matrix": [{"status": s, "mask": m, "anomalies": a, "orders": n}
            for (s, m, a), n in sorted(anomalies_matrix.items())],
        "chronology_by_status": [{"status": s, "anomaly": a, "comparable": n,
            "negative": anomaly_counts[(s, a)]} for (s, a), n in sorted(anomaly_pairs.items())],
        "observed_intervals_by_status": {s: a.result() for s, a in sorted(status_intervals.items())},
        "estimated_delivery_time_of_day_counts": dict(estimate_times),
        "same_day_timestamp_only_delay_seconds": {
            "orders": sum(same_day_seconds.values()),
            "minimum": min(same_day_seconds) if same_day_seconds else None,
            "maximum": max(same_day_seconds) if same_day_seconds else None,
            "under_one_hour": sum(n for seconds, n in same_day_seconds.items() if seconds < 3600)},
        "population_alternatives": {k: a.result() for k, a in populations.items()},
        "strict_chronology_sensitivity": {k: a.result() for k, a in strict_policy.items()},
        "q07_states": states, "threshold_500_state_sets": threshold_sets,
        "q07_lateness_rule_differences_by_qualifying_state": {
            r["state"]: {"orders": len(timestamp_only_by_state[r["state"]]),
                         "order_ids": sorted(timestamp_only_by_state[r["state"]])}
            for r in qualifying},
        "state_rankings_slowest_or_most_late_first": rankings,
        "state_rank_inversions": inversions,
        "q10_review_coverage": {p: dict(c) for p, c in review_coverage.items()},
        "q10_score_groups": q10,
        "differing_order_ids": {k: sorted(v) for k, v in sorted(differing.items())},
        "examples": examples, "synthetic_threshold_counterexamples": synthetic_thresholds,
        "limits": ["No SQL executed; CSV numbers are an independent oracle, not core/mart output",
            "Timestamp values have no supplied timezone; no timezone is invented",
            "Midnight precision does not establish business SLA semantics",
            "No snapshot observation time: undelivered backlog cannot be classified as overdue",
            "Missing-date bounds are identification bounds, not confidence intervals",
            "Finite upper bound on missing completed durations cannot be inferred",
            "Observed review/delivery association does not establish causality"],
    }
    numeric_payload = {k: v for k, v in result.items() if k not in
                       ["source_bindings", "started_utc", "completed_utc", "generated_by"]}
    result["numeric_payload_sha256"] = digest(json.dumps(numeric_payload, ensure_ascii=False,
                                                         sort_keys=True).encode("utf-8"))
    output = HERE / "results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "orders": len(seen),
        "used_inputs_equal_baseline": True, "delivered": populations["delivered"].result(),
        "threshold_sets": threshold_sets, "script_sha256": result["source_bindings"]["script_sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
