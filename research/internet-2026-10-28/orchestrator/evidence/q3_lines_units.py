"""Distinct group metric versus physical source rows; no DB or source writes."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

root = Path(__file__).resolve().parents[4]
data = root / 'data'
names = ['olist_orders_dataset.csv', 'olist_order_items_dataset.csv']
hashes = {n: hashlib.sha256((data / n).read_bytes()).hexdigest() for n in names}
with (data / names[0]).open(encoding='utf-8-sig', newline='') as f:
    delivered = {r['order_id'] for r in csv.DictReader(f) if r['order_status'] == 'delivered'}
n, groups, products = Counter(), defaultdict(set), defaultdict(set)
with (data / names[1]).open(encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        k = r['order_id']
        if k in delivered:
            n[k] += 1
            groups[k].add((r['product_id'], r['seller_id']))
            products[k].add(r['product_id'])
den = len(n)
result = {'method': 'Sol stdlib CSV; delivered orders with items; all purchase dates; no DB',
          'sha256': hashes, 'orders': den, 'physical_item_rows': sum(n.values()),
          'rows_or_units_per_order': str(Decimal(sum(n.values())) / den),
          'distinct_product_seller_groups': sum(map(len, groups.values())),
          'product_seller_groups_per_order': str(Decimal(sum(map(len, groups.values()))) / den),
          'distinct_products_per_order': str(Decimal(sum(map(len, products.values()))) / den),
          'limits': 'Grouped SKU lines are derived; source order_item grain and organizer intent unchanged'}
Path(__file__).with_name('q3-lines-units.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
