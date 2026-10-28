#!/usr/bin/env python3
"""Streaming CSV Q10 sensitivity; run from any cwd, no database or dependencies."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name('results.json')
BASELINE = {
    'olist_orders_dataset.csv': '8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf',
    'olist_order_reviews_dataset.csv': '012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7',
}

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def parse_date(value):
    return datetime.fromisoformat(value) if value else None

def latest(rows, field):
    known = [r for r in rows if r[field] is not None]
    if not known:
        return None, 'all_null'
    maximum = max(r[field] for r in known)
    top = [r for r in known if r[field] == maximum]
    scores = {r['score'] for r in top}
    if len(scores) > 1:
        return None, 'tie_conflicting_scores'
    return next(iter(scores)), 'tie_same_score' if len(top) > 1 else 'unique'

def selftest():
    a = datetime(2018, 1, 1)
    b = datetime(2018, 1, 2)
    rows = [{'score': 1, 'date': a}, {'score': 2, 'date': b}, {'score': 2, 'date': b}, {'score': 5, 'date': None}]
    assert latest(rows, 'date') == (2, 'tie_same_score')
    rows[2]['score'] = 3
    assert latest(rows, 'date') == (None, 'tie_conflicting_scores')
    assert latest([{'score': 1, 'date': None}], 'date') == (None, 'all_null')
    assert latest([{'score': 1, 'date': a}, {'score': 2, 'date': None}], 'date') == (1, 'unique')


def main():
    selftest()
    paths = {name: ROOT / 'data' / name for name in BASELINE}
    hashes = {name: digest(path) for name, path in paths.items()}
    if hashes != BASELINE:
        raise RuntimeError('CSV SHA-256 differs from pinned baseline; refusing to produce results')
    orders = {}
    order_rows = 0
    with paths['olist_orders_dataset.csv'].open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            order_rows += 1
            if row['order_status'] != 'delivered':
                continue
            oid = row['order_id']
            assert oid not in orders, 'Duplicate delivered order id'
            purchase = parse_date(row['order_purchase_timestamp'])
            delivered = parse_date(row['order_delivered_customer_date'])
            estimated = parse_date(row['order_estimated_delivery_date'])
            seconds = (delivered - purchase).total_seconds() if delivered and purchase else None
            orders[oid] = (seconds if seconds is not None and seconds >= 0 else None,
                           delivered.date() > estimated.date() if delivered and estimated else None)
    reviews = defaultdict(list)
    input_rows = 0
    invalid = Counter()
    with paths['olist_order_reviews_dataset.csv'].open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            input_rows += 1
            if row['order_id'] not in orders:
                continue
            raw_score = row['review_score']
            if not raw_score:
                invalid['null_score_rows'] += 1
                continue
            score = int(raw_score)
            if score not in range(1, 6):
                invalid['out_of_range_score_rows'] += 1
                continue
            reviews[row['order_id']].append({'score': score,
                'creation': parse_date(row['review_creation_date']),
                'answer': parse_date(row['review_answer_timestamp']),
                'review_id': row['review_id']})
    policies = ('within_score', 'single_score_only', 'latest_creation', 'latest_answer', 'min_score')
    accum = {p: {s: {'orders_count': 0, 'duration_count': 0, 'duration_seconds': 0,
                      'late_count': 0, 'late_orders': 0} for s in range(1, 6)} for p in policies}
    stats = Counter()
    selection = {p: Counter() for p in ('latest_creation', 'latest_answer')}
    pairs = set()
    duplicate_pair_rows = 0
    unique_group_sets = {p: set() for p in policies}
    for oid, rows in reviews.items():
        scores = {r['score'] for r in rows}
        stats['scored_orders'] += 1
        stats['multi_review_orders'] += len(rows) > 1
        stats['conflicting_score_orders'] += len(scores) > 1
        stats['multi_review_same_score_only_orders'] += len(rows) > 1 and len(scores) == 1
        counts = Counter(r['score'] for r in rows)
        stats['orders_with_repeated_score'] += any(n > 1 for n in counts.values())
        stats['repeated_score_extra_rows'] += sum(n - 1 for n in counts.values())
        stats['review_rows'] += len(rows)
        for row in rows:
            stats['null_creation_rows'] += row['creation'] is None
            stats['null_answer_rows'] += row['answer'] is None
            pair = (oid, row['review_id'])
            duplicate_pair_rows += pair in pairs
            pairs.add(pair)
        if len(rows) > 1:
            for field in ('creation', 'answer'):
                known = {r[field] for r in rows if r[field] is not None}
                stats[f'multi_review_orders_{field}_different_known_timestamps'] += len(known) > 1
                stats[f'repeated_same_score_orders_{field}_different_known_timestamps'] += any(
                    len({r[field] for r in rows if r['score'] == score and r[field] is not None}) > 1
                    for score, n in counts.items() if n > 1)
                stats[f'multi_review_orders_{field}_some_null'] += any(r[field] is None for r in rows)
                stats[f'multi_review_orders_{field}_all_null'] += not known
        choices = {'within_score': scores, 'single_score_only': scores if len(scores) == 1 else set(),
                   'min_score': {min(scores)}}
        for policy, field in (('latest_creation', 'creation'), ('latest_answer', 'answer')):
            score, reason = latest(rows, field)
            selection[policy][reason] += 1
            choices[policy] = {score} if score is not None else set()
        duration, late = orders[oid]
        for policy, selected in choices.items():
            for score in selected:
                unique_group_sets[policy].add((oid, score))
                a = accum[policy][score]
                a['orders_count'] += 1
                if duration is not None:
                    a['duration_count'] += 1
                    a['duration_seconds'] += duration
                if late is not None:
                    a['late_count'] += 1
                    a['late_orders'] += int(late)
    results = {}
    for policy, groups in accum.items():
        results[policy] = {}
        for score, a in groups.items():
            n = a['orders_count']
            results[policy][score] = {**a,
                'duration_coverage_pct': 100 * a['duration_count'] / n if n else None,
                'late_coverage_pct': 100 * a['late_count'] / n if n else None,
                'mean_days': a['duration_seconds'] / a['duration_count'] / 86400 if a['duration_count'] else None,
                'late_pct': 100 * a['late_orders'] / a['late_count'] if a['late_count'] else None}
    stats['delivered_orders'] = len(orders)
    stats['delivered_orders_without_valid_score'] = len(orders) - len(reviews)
    stats['duplicate_review_order_pair_rows'] = duplicate_pair_rows
    differences = {p: {'additional_order_score_pairs': len(unique_group_sets[p] - unique_group_sets['within_score']),
                       'removed_order_score_pairs': len(unique_group_sets['within_score'] - unique_group_sets[p])}
                   for p in policies if p != 'within_score'}
    assert stats['review_rows'] <= input_rows
    assert stats['multi_review_orders'] == stats['conflicting_score_orders'] + stats['multi_review_same_score_only_orders']
    assert all(v['additional_order_score_pairs'] == 0 for v in differences.values())
    assert sum(x['orders_count'] for x in results['single_score_only'].values()) == len(reviews) - stats['conflicting_score_orders']
    assert sum(x['orders_count'] for x in results['within_score'].values()) == len(reviews) + differences['min_score']['removed_order_score_pairs']
    payload = {'scope': 'CSV-only; delivered; valid scores 1-5; no core execution',
        'baseline_project_sha': 'bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4',
        'baseline_manifest_sha256': '357f789cc4034505ef7d8888a649595c7ea67c4d145eb7be0318f546005de3b3',
        'inputs_sha256': hashes, 'input_order_rows': order_rows, 'input_review_rows': input_rows,
        'invalid_score_rows_delivered': dict(invalid), 'selection_outcomes': {k: dict(v) for k, v in selection.items()},
        'diagnostics': dict(stats), 'differences_vs_within_score': differences,
        'latest_answer_vs_min_score_changed_orders': len(unique_group_sets['latest_answer'] - unique_group_sets['min_score']),
        'latest_creation_vs_latest_answer_changed_or_excluded_orders': len(unique_group_sets['latest_answer'] - unique_group_sets['latest_creation']),
        'definitions': {'duration': 'delivered minus purchase in fractional days; require both and nonnegative',
            'late': 'delivered date > estimated date; require both; calendar days in source timezone',
            'latest': 'max non-null timestamp; all-null excluded; tied max with multiple scores excluded; tied max same score counted once',
            'within_score': 'one association per distinct order and valid score; groups overlap',
            'single_score_only': 'only orders with one distinct non-null valid score',
            'min_score': 'one order under smallest valid score'}, 'results': results,
        'selftest': 'PASS: latest timestamp NULL and tie cases'}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f'wrote {OUT}; delivered={len(orders)} scored={len(reviews)}')

if __name__ == '__main__':
    main()
