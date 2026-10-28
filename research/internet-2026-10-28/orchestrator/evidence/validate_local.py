"""Independent Sol checks; reads local CSV, never DB/core or input writes."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / 'data'
OUT = Path(__file__).with_name('sol-independent-check.json')
Z = Decimal('0')
files = {}

def rows(name):
    p = DATA / name
    h = hashlib.sha256()
    with p.open('rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    n = 0
    with p.open(encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        header = r.fieldnames
        for row in r:
            n += 1
            yield row
    files[name] = {'sha256': h.hexdigest(), 'records': n, 'header': header}

orders = {r['order_id']: r for r in rows('olist_orders_dataset.csv')}
items, payments = {}, {}
ic, pc = Counter(), Counter()
for r in rows('olist_order_items_dataset.csv'):
    k = r['order_id']
    items[k] = items.get(k, Z) + Decimal(r['price']) + Decimal(r['freight_value'])
    ic[k] += 1
for r in rows('olist_order_payments_dataset.csv'):
    k = r['order_id']
    payments[k] = payments.get(k, Z) + Decimal(r['payment_value'])
    pc[k] += 1
both = set(items) & set(payments)
deltas = {k: payments[k] - items[k] for k in both}
thresholds = {}
for label, threshold in [('exact_nonzero', Z), ('abs_gt_one_cent', Decimal('.01'))]:
    vals = [d for d in deltas.values() if abs(d) > threshold]
    thresholds[label] = {'count': len(vals), 'sum_delta': str(sum(vals, Z))}
zero_hypothesis = [payments.get(k, Z) - items.get(k, Z) for k in orders]

buyers = defaultdict(set)
customer_ids = set()
for r in rows('olist_customers_dataset.csv'):
    customer_ids.add(r['customer_id'])
    buyers[r['customer_unique_id']].add(r['customer_zip_code_prefix'])
review_payloads = defaultdict(set)
pairs = set()
review_rows = 0
for r in rows('olist_order_reviews_dataset.csv'):
    review_rows += 1
    pairs.add((r['review_id'], r['order_id']))
    review_payloads[r['review_id']].add(tuple(r[k] for k in (
        'review_score', 'review_comment_title', 'review_comment_message',
        'review_creation_date', 'review_answer_timestamp')))
for name in ('olist_products_dataset.csv', 'olist_sellers_dataset.csv',
             'product_category_name_translation.csv'):
    for _ in rows(name):
        pass
monthly = Counter(r['order_purchase_timestamp'][:7] for r in orders.values())
tail = [r for r in orders.values() if r['order_purchase_timestamp'] >= '2018-09-01']
result = {
    'method': 'Independent Sol stdlib CSV + Decimal, local files; no DB/core/third-party code',
    'source_ref_claim_to_compare': 'd9e49802f3e92d09ee94ab9ccc5e457f207a8959',
    'files': files, 'total_csv_records': sum(v['records'] for v in files.values()),
    'finance': {
        'comparison': 'sum(payment_value) - sum(price + freight_value), separately by order_id',
        'population': 'orders with both children, all source statuses',
        'orders': len(orders), 'intersection': len(both),
        'items_only': len(set(items) - set(payments)),
        'payments_only': len(set(payments) - set(items)),
        'thresholds': thresholds,
        'zero_substitution_hypothesis_only': {
            'nonzero_count': sum(d != Z for d in zero_hypothesis),
            'sum_delta': str(sum(zero_hypothesis, Z))},
        'fanout_intersection': {
            'join_rows': sum(ic[k] * pc[k] for k in both),
            'item_amount_correct': str(sum((items[k] for k in both), Z)),
            'item_amount_after_join': str(sum((items[k] * pc[k] for k in both), Z)),
            'payment_correct': str(sum((payments[k] for k in both), Z)),
            'payment_after_join': str(sum((payments[k] * ic[k] for k in both), Z))}},
    'customers': {'customer_ids': len(customer_ids), 'buyers': len(buyers),
                  'buyers_multiple_zip_prefix': sum(len(v) > 1 for v in buyers.values())},
    'reviews': {'records': review_rows, 'distinct_pairs': len(pairs),
                'distinct_review_ids': len(review_payloads),
                'ids_conflicting_full_payload': sum(len(v) > 1 for v in review_payloads.values())},
    'time': {'purchase_month_counts': dict(sorted(monthly.items())),
             'tail_purchase_ge_2018_09_01': len(tail),
             'tail_delivered_status': sum(r['order_status'] == 'delivered' for r in tail),
             'max_purchase': max(r['order_purchase_timestamp'] for r in orders.values()),
             'max_delivered_timestamp_present': max(r['order_delivered_customer_date'] for r in orders.values())},
    'limits': ['Source bytes are local CSV, not proof of DB/raw equality',
               'CSV empty strings compared literally; no SQL NULL assertion',
               'No business cause, extraction as-of, metric approval or model PASS inferred']}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'files'}, ensure_ascii=False))
