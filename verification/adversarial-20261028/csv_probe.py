#!/usr/bin/env python3
"""Streaming input observations, not a SQL oracle or a full DB lifecycle."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
INPUT = 'aab62d7a59f196be051df12466fb21c0da4659b9'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=HERE / 'csv-observations.json')
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.output.is_relative_to(HERE):
        raise SystemExit('Output must be inside OWNED path')
    summary = dict(utc=datetime.now(timezone.utc).isoformat(), input_sha=INPUT,
                   method='streaming_csv_no_db', csv_raw_equality='NOT_RUN', files={}, observations={})
    samples = defaultdict(list)
    counts = Counter()
    review_payloads = {}
    order_scores = defaultdict(set)
    translations = set()
    trans_file = args.csv_dir / 'product_category_name_translation.csv'
    with trans_file.open(newline='', encoding='utf-8-sig') as f:
        translations = {r['product_category_name'] for r in csv.DictReader(f)}
    def sample(label, row, fields):
        counts[label] += 1
        if len(samples[label]) < 2:
            samples[label].append({k: row[k] for k in fields})
    for file in sorted(args.csv_dir.glob('*.csv')):
        digest = hashlib.sha256()
        with file.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(block)
        rows = 0
        with file.open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows += 1
                if file.name == 'olist_orders_dataset.csv':
                    counts['status:' + row['order_status']] += 1
                    if row['order_status'] == 'delivered' and not row['order_delivered_customer_date']:
                        sample('delivered_without_actual_date', row, ('order_id', 'order_status', 'order_delivered_customer_date'))
                    if row['order_delivered_customer_date'] and row['order_purchase_timestamp'] and row['order_delivered_customer_date'] < row['order_purchase_timestamp']:
                        sample('negative_purchase_delivery', row, ('order_id', 'order_purchase_timestamp', 'order_delivered_customer_date'))
                elif file.name == 'olist_order_payments_dataset.csv':
                    if row['payment_value'] == '0.0' or row['payment_value'] == '0.00' or row['payment_value'] == '0':
                        sample('zero_payment', row, tuple(row))
                    if row['payment_installments'] == '0':
                        sample('zero_installments', row, tuple(row))
                elif file.name == 'olist_products_dataset.csv':
                    if not row['product_category_name']:
                        sample('missing_category', row, ('product_id', 'product_category_name'))
                    elif row['product_category_name'] not in translations:
                        sample('untranslated_category', row, ('product_id', 'product_category_name'))
                elif file.name == 'olist_order_reviews_dataset.csv':
                    # Hash full payload; never select a representative score on conflict.
                    payload = tuple((k, row[k]) for k in row if k not in ('review_id', 'order_id'))
                    rid = row['review_id']
                    if rid in review_payloads and review_payloads[rid] != payload:
                        sample('review_id_different_payload_association', row, ('review_id', 'order_id', 'review_score'))
                    else:
                        review_payloads[rid] = payload
                    score = row['review_score']
                    if score in order_scores[row['order_id']]:
                        sample('repeated_order_score_association', row, ('review_id', 'order_id', 'review_score'))
                    order_scores[row['order_id']].add(score)
        summary['files'][file.name] = dict(sha256=digest.hexdigest(), rows=rows, header=reader.fieldnames)
    summary['observations'] = dict(counts)
    summary['examples'] = dict(samples)
    summary['orders_with_multiple_known_scores'] = sum(len(s - {''}) > 1 for s in order_scores.values())
    lock = json.loads(subprocess.check_output(['git', 'show', INPUT + ':tests/model/input-manifest.lock.json'], cwd=HERE.parents[1]))
    summary['pinned_lock_blob_sha256'] = hashlib.sha256(json.dumps(lock, sort_keys=True).encode()).hexdigest()
    summary['pinned_lock_matches'] = {}
    for record in lock['files']:
        actual = summary['files'][record['file']]
        summary['pinned_lock_matches'][record['file']] = all(actual[key] == record[key] for key in ('sha256', 'rows', 'header'))
    if len(summary['files']) != 8 or not all(summary['pinned_lock_matches'].values()):
        raise RuntimeError('CSV files differ from pinned input lock')
    summary['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(files=len(summary['files']), counts=dict(counts), output=str(args.output)), ensure_ascii=False))


if __name__ == '__main__':
    main()
