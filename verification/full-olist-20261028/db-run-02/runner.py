#!/usr/bin/env python3
"""Pinned full CSV oracle and optional bounded, read-only existing-core check.

Never starts a server, loads raw, executes DDL, or builds/rebuilds the model.
Reads code with git show, so an old/dirty checkout is not an input dependency.
Only aggregate results and content digests are written. Python 3.11+, stdlib
for CSV mode; existing psycopg 3 for DB mode. No dependencies are installed.
"""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

INPUT = 'aab62d7a59f196be051df12466fb21c0da4659b9'
SQL_INPUT = '99bcbb366720f912ef6017a40aa5dbd6a671a8a4'
REQUIREMENTS = '558f0f6a38110acc9fcf4386a7e53ece973aedf5'
D = Decimal


def sha(b):
    return hashlib.sha256(b).hexdigest()


def file_sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def blob(repo, ref, path):
    return subprocess.check_output(['git', '-C', str(repo), 'show', ref + ':' + path])


def norm(v):
    if isinstance(v, Decimal):
        return format(v.normalize(), 'f')
    if isinstance(v, (datetime, date)):
        return v.isoformat(sep=' ') if isinstance(v, datetime) else v.isoformat()
    if isinstance(v, (list, tuple)):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {k: norm(x) for k, x in v.items()}
    return v


def encoded(v):
    return json.dumps(norm(v), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


class TrackedLines:
    def __init__(self, f):
        self.f, self.parts = f, []

    def __iter__(self):
        return self

    def __next__(self):
        line = next(self.f)
        self.parts.append(line)
        return line


def quoted_flags(record):
    """Retain PG COPY distinction between unquoted NULL and quoted empty text."""
    flags, start, inside, i = [], True, False, 0
    while i < len(record):
        c = record[i]
        if start:
            flags.append(c == '"')
            inside, start = c == '"', False
            if inside:
                i += 1
                continue
        if c == '"' and inside:
            if i + 1 < len(record) and record[i + 1] == '"':
                i += 2
                continue
            inside = False
        elif c == ',' and not inside:
            start = True
        elif c in '\r\n' and not inside:
            break
        i += 1
    return flags


def csv_rows(path, expected_header=None):
    with path.open(encoding='utf-8-sig', newline='') as f:
        lines = TrackedLines(f)
        reader = csv.reader(lines, strict=True)
        header = next(reader)
        lines.parts.clear()
        if expected_header is not None and header != expected_header:
            raise ValueError('CSV header differs: ' + path.name)
        for row in reader:
            flags = quoted_flags(''.join(lines.parts))
            lines.parts.clear()
            if len(row) != len(header) or len(flags) != len(header):
                raise ValueError('CSV record width differs: ' + path.name)
            yield dict(zip(header, [None if v == '' and not q else v for v, q in zip(row, flags)]))


def multiset(rows):
    c = Counter(hashlib.sha256(encoded(r)).digest() for r in rows)
    h = hashlib.sha256()
    for digest, n in sorted(c.items()):
        h.update(digest)
        h.update(n.to_bytes(8, 'big'))
    return {'rows': sum(c.values()), 'distinct_row_hashes': len(c), 'multiset_sha256': h.hexdigest()}


def ratio(a, b):
    return D(a) / D(b) if b else None


def rounded(v, places=2):
    return v.quantize(D(10) ** -places, rounding=ROUND_HALF_UP) if v is not None else None


def dec(v):
    return D(v) if v is not None else None


def integer(v):
    return int(v) if v is not None else None


def stamp(v):
    return datetime.fromisoformat(v) if v is not None else None


def zip_valid(v):
    return v.zfill(5) if v and re.fullmatch(r'[0-9]{1,5}', v) else None


def bind_inputs(repo, ref, data):
    pin = json.loads(blob(repo, ref, 'tests/model/input-manifest.lock.json'))
    result = []
    for entry in pin['files']:
        p = data / entry['file']
        digest = file_sha(p)
        if digest != entry['sha256'] or p.stat().st_size != entry['bytes']:
            raise ValueError('Pinned CSV bytes differ: ' + p.name)
        header = entry['header']
        fp = multiset(tuple(r[c] for c in header) for r in csv_rows(p, header))
        if fp['rows'] != entry['rows']:
            raise ValueError('Pinned CSV row count differs: ' + p.name)
        result.append({**entry, **fp})
    return result


class Oracle:
    def __init__(self, data):
        self.data = data
        self.customers = {r['customer_id']: r for r in self.read('customers')}
        self.products = {r['product_id']: r for r in self.read('products')}
        self.sellers = {r['seller_id']: r for r in self.read('sellers')}
        self.translations = {r['product_category_name']: r['product_category_name_english'] for r in self.read('translation')}
        self.orders = {}
        self.event_dates = [date(2016, 9, 1), date(2018, 8, 31)]
        for r in self.read('orders'):
            r = dict(r)
            r.update(self.customers[r['customer_id']])
            for k in list(r):
                if k.startswith('order_') and k not in ('order_id', 'order_status'):
                    r[k] = stamp(r[k])
                    if r[k]:
                        self.event_dates.append(r[k].date())
            self.orders[r['order_id']] = r
        self.items, self.payments, self.scores = {}, {}, defaultdict(set)

    def read(self, kind):
        suffix = {'items': 'order_items', 'payments': 'order_payments', 'reviews': 'order_reviews'}.get(kind, kind)
        name = 'product_category_name_translation.csv' if kind == 'translation' else f'olist_{suffix}_dataset.csv'
        return csv_rows(self.data / name)

    def measure(self, o):
        p, d, e = (o[k] for k in ('order_purchase_timestamp', 'order_delivered_customer_date', 'order_estimated_delivery_date'))
        delivered = o['order_status'] == 'delivered'
        seconds = int((d - p).total_seconds()) if delivered and d and p and d >= p else None
        day = d.date() > e.date() if delivered and d and e else None
        timestamp = d > e if delivered and d and e else None
        return seconds, day, timestamp

    @staticmethod
    def measured(rows):
        rows = list(rows)
        durations = [r[0] for r in rows if r[0] is not None]
        late = [r[1] for r in rows if r[1] is not None]
        return dict(orders_count=len(rows), duration_denominator=len(durations),
                    avg_delivery_days=ratio(sum(durations), len(durations) * 86400),
                    late_denominator=len(late), late_orders=sum(late), late_pct=ratio(100 * sum(late), len(late)))

    def answers(self):
        prices = {'all_statuses': defaultdict(set), 'delivered': defaultdict(set)}
        seller = defaultdict(lambda: [set(), 0, set(), 0, D(0)])
        category = defaultdict(lambda: [0, D(0)])
        for r in self.read('items'):
            oid, pid, sid = (r[k] for k in ('order_id', 'product_id', 'seller_id'))
            o = self.orders[oid]
            price, freight = dec(r['price']), dec(r['freight_value'])
            if price is None or freight is None:
                raise ValueError('This pinned full oracle requires complete baseline item money')
            a = self.items.setdefault(oid, [0, D(0), D(0), set()])
            a[0] += 1; a[1] += price; a[2] += price + freight; a[3].add((pid, sid))
            self.event_dates.append(stamp(r['shipping_limit_date']).date())
            prices['all_statuses'][pid].add(price)
            a = seller[sid]; a[2].add(oid); a[3] += 1
            if o['order_status'] == 'delivered':
                prices['delivered'][pid].add(price)
                a[0].add(oid); a[1] += 1; a[4] += price
                cat = self.products[pid]['product_category_name']
                a = category[cat]; a[0] += 1; a[1] += price
        q9state = defaultdict(list)
        q9types = defaultdict(list)
        for r in self.read('payments'):
            oid = r['order_id']; o = self.orders[oid]
            amount, parts = dec(r['payment_value']), integer(r['payment_installments'])
            if amount is None or parts is None:
                raise ValueError('This pinned full oracle requires complete baseline payments')
            a = self.payments.setdefault(oid, [0, D(0)]); a[0] += 1; a[1] += amount
            v = (amount, parts, r['payment_type'])
            q9types[('all_snapshot', r['payment_type'])].append(v)
            if o['order_purchase_timestamp'] and o['order_purchase_timestamp'].year == 2018:
                q9state[o['customer_state']].append(v)
                q9types[('purchase_2018', r['payment_type'])].append(v)
        for r in self.read('reviews'):
            if r['review_score'] is not None:
                self.scores[r['order_id']].add(int(r['review_score']))
            for k in ('review_creation_date', 'review_answer_timestamp'):
                if r[k]: self.event_dates.append(stamp(r[k]).date())
        delivered = [o for o in self.orders.values() if o['order_status'] == 'delivered']
        q = {}
        q['q01'] = []
        for n in range(24):
            month = date(2016 + (8 + n) // 12, (8 + n) % 12 + 1, 1)
            placed = [o for o in self.orders.values() if o['order_purchase_timestamp'] and o['order_purchase_timestamp'].date().replace(day=1) == month]
            ds = [o for o in placed if o['order_status'] == 'delivered']
            units = sum(self.items.get(o['order_id'], [0])[0] for o in ds)
            revenue = sum((self.items[o['order_id']][1] for o in ds), D(0))
            q['q01'].append(dict(month_start=month, orders_placed=len(placed), orders_delivered=len(ds),
                orders_revenue_eligible=len(ds), revenue_orders_without_items=0,
                revenue_item_rows_count=units, revenue_price_valid_count=units,
                revenue_price_missing_count=0, item_revenue=revenue, item_revenue_known_sum=revenue))
        q['q02'] = []
        for rank, (sid, a) in enumerate(sorted(seller.items(), key=lambda x: (-x[1][4], x[0]))[:10], 1):
            s = self.sellers[sid]
            q['q02'].append(dict(seller_id=sid, seller_city=s['seller_city'], seller_state=s['seller_state'],
                orders_delivered=len(a[0]), units_delivered=a[1], orders_all_statuses=len(a[2]), units_all_statuses=a[3],
                orders_revenue_eligible=len(a[0]), revenue_item_rows_count=a[1], revenue_price_valid_count=a[1],
                revenue_price_missing_count=0, item_revenue=a[4], item_revenue_known_sum=a[4], revenue_rank=rank,
                revenue_candidate_sellers=len(seller), incomplete_revenue_sellers=0, incomplete_revenue_seller_ids=[],
                ranking_is_complete=True, ranking_scope='complete_population'))
        gmv = [self.items[o['order_id']][2] for o in delivered if o['order_id'] in self.items]
        pay = [self.payments[o['order_id']][1] for o in delivered if o['order_id'] in self.payments]
        units = sum(self.items.get(o['order_id'], [0])[0] for o in delivered)
        lines = sum(len(self.items[o['order_id']][3]) for o in delivered if o['order_id'] in self.items)
        q['q03'] = [dict(n_delivered_orders=len(delivered), n_order_gmv=len(gmv), n_excluded_order_gmv=len(delivered)-len(gmv),
            order_gmv_sum=sum(gmv), avg_order_gmv=ratio(sum(gmv), len(gmv)), avg_order_gmv_rounded=rounded(ratio(sum(gmv), len(gmv))),
            n_payment_amount=len(pay), n_excluded_payment_amount=len(delivered)-len(pay), payment_amount_sum=sum(pay),
            avg_payment_amount=ratio(sum(pay), len(pay)), avg_payment_amount_rounded=rounded(ratio(sum(pay), len(pay))),
            source_rows_count=units, units_count=units, distinct_product_seller_lines_count=lines,
            avg_source_rows=ratio(units, len(delivered)), avg_units=ratio(units, len(delivered)),
            avg_distinct_product_seller_lines=ratio(lines, len(delivered)))]
        for key, population, label in [('q04', list(self.orders.values()), 'all_snapshot'),
            ('q04_window', [o for o in self.orders.values() if o['order_purchase_timestamp'] and datetime(2016,9,1) <= o['order_purchase_timestamp'] < datetime(2018,9,1)], '[2016-09-01,2018-09-01)')]:
            counts = Counter(o['customer_unique_id'] for o in population)
            repeats = sum(n > 1 for n in counts.values()); pct = ratio(100 * repeats, len(counts))
            row = dict(observation_window=label, buyers=len(counts), repeat_buyers=repeats,
                repeat_buyer_ratio=ratio(repeats, len(counts)), repeat_buyer_pct=pct,
                repeat_buyer_pct_rounded=rounded(pct), orders_count=len(population))
            if key == 'q04': row['unknown_purchase_timestamp_orders'] = sum(o['order_purchase_timestamp'] is None for o in population)
            q[key] = [row]
        total = sum((a[1] for a in category.values()), D(0)); total_units = sum(a[0] for a in category.values())
        q['q05'] = []
        for cat in sorted({r['product_category_name'] for r in self.products.values()} | set(self.translations), key=lambda x: (x is None, x or '')):
            n, value = category.get(cat, [0, D(0)])
            q['q05'].append(dict(category_key='pt:'+cat if cat is not None else 'unknown', name_pt=cat,
                name_en=self.translations.get(cat), is_unknown=cat is None, is_translated=self.translations.get(cat) is not None,
                revenue_item_rows_count=n, revenue_price_valid_count=n, revenue_price_missing_count=0,
                item_revenue=value, item_revenue_known_sum=value, total_item_revenue=total,
                total_revenue_item_rows_count=total_units, total_revenue_price_valid_count=total_units,
                revenue_pct=ratio(100*value,total), revenue_pct_rounded=rounded(ratio(100*value,total))))
        self.winners = {}
        for pop, groups in prices.items():
            maximum = max(map(len, groups.values()))
            self.winners[pop] = {pid: len(ps) for pid, ps in groups.items() if len(ps) == maximum}
        history = Counter()
        for r in self.read('items'):
            o = self.orders[r['order_id']]
            for pop in self.winners:
                if r['product_id'] in self.winners[pop] and (pop == 'all_statuses' or o['order_status'] == 'delivered'):
                    dt = o['order_purchase_timestamp'].date() if o['order_purchase_timestamp'] else None
                    history[(pop,r['product_id'],dt,dec(r['price']))] += 1
        q['q06'] = [dict(population=p, product_id=pid, distinct_prices=self.winners[p][pid],
            units_with_unknown_price=0, purchase_date=dt, price=price, units_sold=n) for (p,pid,dt,price),n in sorted(history.items())]
        q['q07'], q['q10'], q['q10_coverage'] = [], [], []
        for pop in ('all_statuses', 'delivered'):
            population = list(self.orders.values()) if pop == 'all_statuses' else delivered
            for state in sorted({o['customer_state'] for o in population}):
                group = [o for o in population if o['customer_state'] == state]
                if len(group) >= 500:
                    for basis, idx in [('calendar_day', 1), ('timestamp', 2)]:
                        q['q07'].append(dict(population=pop, customer_state=state, late_basis=basis,
                            **self.measured((self.measure(o)[0], self.measure(o)[idx]) for o in group)))
            for policy in ('single_score_only', 'within_score'):
                for basis, idx in [('calendar_day', 1), ('timestamp', 2)]:
                    for score in range(1,6):
                        group = [o for o in population if score in self.scores[o['order_id']] and
                                 (policy == 'within_score' or len(self.scores[o['order_id']]) == 1)]
                        q['q10'].append(dict(population=pop,score_policy=policy,late_basis=basis,review_score=score,
                            **self.measured((self.measure(o)[0], self.measure(o)[idx]) for o in group)))
            sets = [self.scores[o['order_id']] for o in population]
            q['q10_coverage'].append(dict(population=pop, orders_count=len(population),
                orders_without_score=sum(not s for s in sets), orders_with_multiple_scores=sum(len(s)>1 for s in sets),
                orders_in_multiple_valid_score_groups=sum(len(s & {1,2,3,4,5})>1 for s in sets),
                orders_with_out_of_range_score=sum(bool(s-{1,2,3,4,5}) for s in sets)))
        statuses = Counter(o['order_status'] for o in self.orders.values())
        q['q08'] = [dict(order_status=s,orders_count=n,orders_pct=ratio(100*n,len(self.orders)),
            orders_without_items=sum(o['order_status']==s and oid not in self.items for oid,o in self.orders.items()))
            for s,n in sorted(statuses.items(),key=lambda x:(-x[1],x[0]))]
        q['q09_state'] = []
        for state, rows in sorted(q9state.items()):
            credit = [r[1] for r in rows if r[2] == 'credit_card']
            amount=sum(r[0] for r in rows)
            q['q09_state'].append(dict(customer_state=state,payment_count=len(rows),amount_denominator=len(rows),
                payment_amount=amount,known_payment_amount_sum=amount,installments_denominator=len(rows),
                avg_installments_all_types=ratio(sum(r[1] for r in rows),len(rows)),credit_installments_denominator=len(credit),
                avg_installments_credit_card=ratio(sum(credit),len(credit))))
        q['q09_methods'] = [dict(period=p,payment_type=t,payment_count=len(rows),installments_denominator=len(rows),
            avg_installments=ratio(sum(r[1] for r in rows),len(rows))) for (p,t),rows in sorted(q9types.items())]
        return q

    def core_expected(self):
        """Every aab dimension/fact business column, including all source text."""
        def projected(kind, conversions=None, rename=None):
            conversions, rename = conversions or {}, rename or {}
            return ({rename.get(k,k):conversions.get(k,lambda x:x)(v) for k,v in r.items()} for r in self.read(kind))
        for kind,table,casts,renames in [
            ('items','fact_order_item',dict(order_item_id=integer,price=dec,freight_value=dec,shipping_limit_date=stamp),{'shipping_limit_date':'shipping_limit_at'}),
            ('payments','fact_payment',dict(payment_sequential=integer,payment_installments=integer,payment_value=dec),{}),
            ('reviews','fact_review',dict(review_score=integer,review_creation_date=stamp,review_answer_timestamp=stamp),{}),
        ]:
            yield table, projected(kind,casts,renames)
        yield 'fact_order', (dict(o,customer_zip_code_prefix_validated=zip_valid(o['customer_zip_code_prefix'])) for o in self.orders.values())
        yield 'dim_customer', ({'customer_unique_id':uid} for uid in sorted({r['customer_unique_id'] for r in self.customers.values()}))
        yield 'dim_customer_context', (dict(r,customer_zip_code_prefix_validated=zip_valid(r['customer_zip_code_prefix'])) for r in self.customers.values())
        yield 'dim_seller', (dict(r,seller_zip_code_prefix_validated=zip_valid(r['seller_zip_code_prefix'])) for r in self.sellers.values())
        def products():
            for r in self.products.values():
                x={k:(integer(v) if k in ('product_name_lenght','product_description_lenght','product_photos_qty') else dec(v) if k.endswith(('_g','_cm')) else v) for k,v in r.items() if k != 'product_category_name'}
                x['category_key']='unknown' if r['product_category_name'] is None else 'pt:'+r['product_category_name']
                yield x
        yield 'dim_product', products()
        def categories():
            yield dict(category_key='unknown',name_pt=None,name_en=None,is_unknown=True,is_translated=False,has_translation_row=False)
            domain={r['product_category_name'] for r in self.products.values()} | set(self.translations)
            for cat in sorted(domain-{None}):
                yield dict(category_key='pt:'+cat,name_pt=cat,name_en=self.translations.get(cat),is_unknown=False,
                    is_translated=self.translations.get(cat) is not None,has_translation_row=cat in self.translations)
        yield 'dim_category', categories()
        yield 'dim_order_status', (dict(order_status=s,is_revenue=s=='delivered') for s in sorted({o['order_status'] for o in self.orders.values()} | {'delivered','shipped','canceled','unavailable','invoiced','processing','created','approved'}))
        def calendar():
            day,last=min(self.event_dates),max(self.event_dates)
            while day <= last:
                iso=day.isocalendar()
                yield dict(date_day=day,month_start=day.replace(day=1),year_number=day.year,quarter_number=(day.month-1)//3+1,
                    month_number=day.month,day_of_month=day.day,iso_year=iso.year,iso_week=iso.week,iso_day_of_week=iso.weekday,is_weekend=iso.weekday>=6)
                day+=timedelta(days=1)
        yield 'dim_date', calendar()


def compare_rows(actual, expected, tolerance=D('0.000000000001')):
    """Order independent comparison with exact keys/NULLs and numeric tolerance."""
    def key(r):
        return encoded({k:v for k,v in r.items() if isinstance(v,(str,date)) or v is None or isinstance(v,bool)})
    actual,expected=sorted(actual,key=key),sorted(expected,key=key)
    if len(actual)!=len(expected):
        raise ValueError(f'Output row count differs: {len(actual)} != {len(expected)}')
    for a,e in zip(actual,expected):
        if a.keys()!=e.keys():
            raise ValueError('Output column set differs')
        for k,v in e.items():
            x=a[k]
            if isinstance(v,(int,Decimal,float)) and not isinstance(v,bool) and x is not None:
                ok=abs(D(str(x))-D(str(v)))<=tolerance
            else:
                ok=norm(x)==norm(v)
            if not ok:
                raise ValueError('Output mismatch in column '+k+'; row contents omitted')
    return {'status':'pass','rows':len(actual),'output_sha256':sha(encoded(actual)),'numeric_absolute_tolerance':str(tolerance)}


def published_comparisons(repo,ref,q):
    pay=json.loads(blob(repo,ref,'docs/phase-20261028/experiments/payments-prices/results.json'))
    delivery=json.loads(blob(repo,ref,'docs/phase-20261028/experiments/delivery-data/results.json'))
    review=json.loads(blob(repo,ref,'docs/phase-20261028/experiments/review-data/results.json'))
    checks={}
    def check(name,actual,expected,tol=D('0.000000000001')):
        checks[name]=compare_rows(actual,expected,tol)
    winners={}
    for r in q['q06']: winners.setdefault(r['population'],{})[r['product_id']]=r['distinct_prices']
    if winners != {p:{pid:v['max_distinct_prices'] for pid in v['product_ids']} for p,v in pay['q6']['winners'].items()}:
        raise ValueError('Q6 published winners differ')
    hist=Counter()
    for r in pay['q6']['winner_history_by_seller_day_price']:
        hist[(r['population'],r['product_id'],r['purchase_date'],D(r['price']))]+=r['units']
    check('q06_winner_day_price_all_rows', [{k:r[k] for k in ('population','product_id','purchase_date','price','units_sold')} for r in q['q06']],
          [dict(population=p,product_id=pid,purchase_date=dt,price=price,units_sold=n) for (p,pid,dt,price),n in hist.items()])
    for key,dimension in [('q09_state','state'),('q09_methods','type')]:
        published=[]
        for r in pay['q9']['aggregates']:
            if r['population']!='all_statuses' or r['dimension']!=dimension:continue
            if dimension=='state':
                if r['period']!='purchase_2018':continue
                published.append(dict(customer_state=r['key'],payment_count=r['payment_rows'],amount_denominator=r['known_amount_count'],
                    payment_amount=D(r['amount_cents'])/100,known_payment_amount_sum=D(r['amount_cents'])/100,
                    installments_denominator=r['installments_count'],avg_installments_all_types=ratio(r['installments_sum'],r['installments_count']),
                    credit_installments_denominator=r['credit_installments_count'],avg_installments_credit_card=ratio(r['credit_installments_sum'],r['credit_installments_count'])))
            else:
                published.append(dict(period=r['period'],payment_type=r['key'],payment_count=r['payment_rows'],
                    installments_denominator=r['installments_count'],avg_installments=ratio(r['installments_sum'],r['installments_count'])))
        check(key+'_all_rows',q[key],published)
    def delivery_row(r,pop,basis):
        duration=r['durations']['purchase_to_delivery']; late=r['lateness']
        return dict(population=pop,late_basis=basis,orders_count=r['orders_count'],duration_denominator=duration['denominator'],
            avg_delivery_days=ratio(duration['sum_seconds'],duration['denominator']*86400),late_denominator=late['denominator'],
            late_orders=late[basis+'_late_orders'],late_pct=ratio(100*late[basis+'_late_orders'],late['denominator']))
    published=[]
    for r in delivery['q07_states']:
        for pop in ('all_statuses','delivered'):
            if r[pop]['orders_count']>=500:
                for basis in ('calendar_day','timestamp'):
                    published.append(dict(customer_state=r['state'],**delivery_row(r[pop],pop,basis)))
    check('q07_all_variants_all_rows',q['q07'],published)
    published=[]
    for r in delivery['q10_score_groups']:
        for basis in ('calendar_day','timestamp'):
            published.append(dict(score_policy=r['score_policy'],review_score=r['score'],**delivery_row(r,r['population'],basis)))
    check('q10_all_variants_all_rows',q['q10'],published)
    for policy in ('within_score','single_score_only'):
        selected=[{k:r[k] for k in ('review_score','orders_count','duration_denominator','avg_delivery_days','late_denominator','late_orders','late_pct')}
                  for r in q['q10'] if r['population']=='delivered' and r['late_basis']=='calendar_day' and r['score_policy']==policy]
        expected=[dict(review_score=int(score),orders_count=r['orders_count'],duration_denominator=r['duration_count'],
            avg_delivery_days=ratio(r['duration_seconds'],r['duration_count']*86400),late_denominator=r['late_count'],
            late_orders=r['late_orders'],late_pct=ratio(100*r['late_orders'],r['late_count'])) for score,r in review['results'][policy].items()]
        check('q10_second_review_oracle_'+policy,selected,expected)
    check('q08_statuses',[dict(order_status=r['order_status'],orders_count=r['orders_count']) for r in q['q08']],
          [dict(order_status=s,orders_count=n) for s,n in delivery['statuses'].items()])
    cov=[dict(population=p,orders_count=r['orders'],orders_without_score=r['no_valid_score'],orders_with_multiple_scores=r['multiple_distinct_scores'],
              orders_in_multiple_valid_score_groups=r['multiple_distinct_scores'],orders_with_out_of_range_score=0) for p,r in delivery['q10_review_coverage'].items()]
    check('q10_coverage_all_rows',q['q10_coverage'],cov)
    return checks


def regression(q):
    actual={'months':len(q['q01']),'orders_placed':sum(r['orders_placed'] for r in q['q01']),
        'item_revenue':sum(r['item_revenue'] for r in q['q01']), 'empty_november':q['q01'][2]['orders_placed'],
        'top_seller_revenue':q['q02'][0]['item_revenue'],'top_seller_delivered_orders':q['q02'][0]['orders_delivered'],
        'top_seller_units':q['q02'][0]['units_delivered'],'avg_gmv':q['q03'][0]['avg_order_gmv_rounded'],
        'n_gmv':q['q03'][0]['n_order_gmv'],'avg_payment':q['q03'][0]['avg_payment_amount_rounded'],
        'n_payment':q['q03'][0]['n_payment_amount'],'buyers':q['q04'][0]['buyers'],'repeat_buyers':q['q04'][0]['repeat_buyers'],
        'repeat_pct':q['q04'][0]['repeat_buyer_pct_rounded'],'window_buyers':q['q04_window'][0]['buyers'],
        'window_repeat_buyers':q['q04_window'][0]['repeat_buyers'],'categories':len(q['q05']),
        'top_category_revenue':max(r['item_revenue'] for r in q['q05'])}
    expected=dict(months=24,orders_placed=99421,item_revenue=D('13221498.11'),empty_november=0,top_seller_revenue=D('226987.93'),
        top_seller_delivered_orders=1124,top_seller_units=1148,avg_gmv=D('159.88'),n_gmv=96478,avg_payment=D('159.86'),
        n_payment=96477,buyers=96096,repeat_buyers=2997,repeat_pct=D('3.12'),window_buyers=96090,window_repeat_buyers=2987,
        categories=74,top_category_revenue=D('1233131.72'))
    if actual!=expected:raise ValueError('Q1–Q5 baseline regression differs')
    return {'status':'pass','scope':'CSV oracle only','controls':actual}


def statements(text):
    # Source files contain SELECT/CTE only, no strings with semicolons. Reject any
    # unsupported shape before DB access. This is not a general SQL parser.
    text=re.sub(r'--[^\n]*','',text)
    result=[s.strip() for s in text.split(';') if s.strip()]
    if not result or any(not re.match(r'^(SELECT|WITH)\b',s,re.I) for s in result) or '\\' in text:
        raise ValueError('Expected only trusted pinned SELECT statements')
    return result


def db_check(args,report,entries,oracle,q):
    import psycopg
    from psycopg import sql
    from psycopg.rows import dict_row
    # Endpoint is explicit and project-local; do not consume ambient services,
    # DATABASE_URL or DSNs. Authentication uses the user's existing libpq config.
    params=dict(host=args.host,port=args.port,dbname=args.database,user=args.user,connect_timeout=3,
                options='-c default_transaction_read_only=on -c statement_timeout=20000 -c lock_timeout=2000 -c idle_in_transaction_session_timeout=60000')
    db={'status':'pending','endpoint':{k:params[k] for k in ('host','port','dbname','user')},'atomic_build_rebuild_rollback':'not_run'}
    report['database']=db
    try:
        conn=psycopg.connect(**params,autocommit=True,row_factory=dict_row)
    except psycopg.Error as exc:
        # No DSN or exception text: a libpq error can contain password/service.
        db.update(status='unavailable',error_type=type(exc).__name__,sqlstate=exc.sqlstate,
                  detail='Connection to explicitly selected local project endpoint failed; no SQL executed')
        return False
    with conn:
        with conn.cursor() as cur:
            cur.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
            cur.execute("SET LOCAL TimeZone='UTC'; SET LOCAL DateStyle='ISO,YMD'; SET LOCAL work_mem='4MB'; SET LOCAL max_parallel_workers_per_gather=0")
            cur.execute("SELECT current_setting('server_version_num')::int AS version_num,current_database() AS database,current_user AS role,current_setting('transaction_read_only') AS read_only,current_setting('transaction_isolation') AS isolation,pg_current_snapshot()::text AS snapshot")
            db['identity']=cur.fetchone()
            if not 160000<=db['identity']['version_num']<170000 or db['identity']['database']!=args.database:
                raise ValueError('Endpoint identity is not expected PG16 project database')
            cur.execute("SELECT nspname FROM pg_namespace WHERE nspname IN ('raw','core','mart') ORDER BY nspname")
            db['schemas']=[r['nspname'] for r in cur.fetchall()]
            if db['schemas']!=['core','mart','raw']:raise ValueError('Missing project schemas')
            cur.execute("SELECT n.nspname||'.'||c.relname AS relation,has_table_privilege(c.oid,'SELECT') AS can_select FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('raw','core','mart') AND c.relkind IN ('r','v','m','p') ORDER BY 1")
            db['select_rights']=cur.fetchall()
            db['code_binding']='existing core; stored view definitions fingerprinted below, build origin not inferred'
            cur.execute("SELECT n.nspname||'.'||c.relname AS relation,pg_get_viewdef(c.oid,true) AS definition FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='mart' AND c.relkind='v' ORDER BY 1")
            db['view_definitions_sha256']={r['relation']:sha(r['definition'].encode()) for r in cur.fetchall()}
        if args.mode=='db-probe':
            conn.execute('ROLLBACK');db['status']='identity_only';return False
        db['raw_binding']={}
        for i,e in enumerate(entries):
            columns=[sql.Identifier(c) for c in e['header']]
            query=sql.SQL('SELECT {} FROM {}').format(sql.SQL(',').join(columns),sql.Identifier(*e['table'].split('.')))
            with conn.cursor(name=f'raw_{i}') as c:
                c.execute(query)
                actual=multiset(tuple(r[k] for k in e['header']) for r in c)
            expected={k:e[k] for k in actual}
            if actual!=expected:raise ValueError('CSV/raw business multiset mismatch: '+e['table'])
            with conn.cursor() as c:
                c.execute(sql.SQL('SELECT count(*) AS n FROM {} WHERE _source_file IS DISTINCT FROM %s').format(sql.Identifier(*e['table'].split('.'))),(e['file'],))
                if c.fetchone()['n']:raise ValueError('Raw source lineage mismatch: '+e['table'])
            db['raw_binding'][e['table']]={'status':'pass',**actual}
        db['core_binding']={}
        for i,(table,rows) in enumerate(oracle.core_expected()):
            expected=multiset(rows)
            with conn.cursor(name=f'core_{i}') as c:
                c.execute(sql.SQL('SELECT * FROM {}').format(sql.Identifier('core',table)))
                actual=multiset(c)
            if actual!=expected:raise ValueError('CSV/core business multiset mismatch: '+table)
            db['core_binding'][table]={'status':'pass',**actual}
        db['queries']={}
        db_outputs={}
        for key,expected in q.items():
            if key.startswith(('q01','q02','q03','q04','q05')):
                path='answers/'+key+'.sql';ref=args.input_ref;index=0
            else:
                path='answers/q06-q10/'+('q09' if key.startswith('q09') else key)+'.sql';ref=SQL_INPUT;index=1 if key=='q09_methods' else 0
            raw=blob(args.repo,ref,path)
            query=statements(raw.decode())[index]
            with conn.cursor() as c:
                c.execute(query);actual=c.fetchall()
            db_outputs[key]=actual
            db['queries'][key]={'source_commit':ref,'file':path,'source_file_sha256':sha(raw),
                'executed_statement_sha256':sha(query.encode()),**compare_rows(actual,expected)}
        # Integrated SELECT files are a distinct check, never substituted for
        # exact original CTE queries when the older core lacks their views.
        db['integrated_queries']={}
        for key in ('q06','q07','q08','q09_state','q09_methods','q10','q10_coverage'):
            path='answers/q06-q10/'+('q09' if key.startswith('q09') else key)+'.sql'
            raw=blob(args.repo,args.input_ref,path);query=statements(raw.decode())[1 if key=='q09_methods' else 0]
            conn.execute('SAVEPOINT integrated_select')
            try:
                with conn.cursor() as c:
                    c.execute(query);actual=c.fetchall()
                db['integrated_queries'][key]={'source_file_sha256':sha(raw),**compare_rows(actual,q[key])}
            except psycopg.errors.UndefinedTable:
                conn.execute('ROLLBACK TO SAVEPOINT integrated_select')
                db['integrated_queries'][key]={'status':'not_run','reason':'integrated mart view absent on existing core'}
            conn.execute('RELEASE SAVEPOINT integrated_select')
        conn.execute('ROLLBACK')
        (args.output_dir/'db-results.json').write_bytes(encoded(db_outputs)+b'\n')
        db['results_sha256']=file_sha(args.output_dir/'db-results.json')
        db['status']='read_only_full_select_pass'
        return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--input-ref',default=INPUT)
    p.add_argument('--data-dir',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--mode',choices=['csv','db-probe','db-readonly'],default='csv')
    p.add_argument('--host',choices=['127.0.0.1','localhost'],default='127.0.0.1')
    p.add_argument('--port',type=int,default=5432)
    p.add_argument('--database',default='marketplace')
    p.add_argument('--user',default='hack')
    p.add_argument('--existing-project-endpoint',action='store_true',help='confirm discovery/ownership of this existing validation endpoint')
    args=p.parse_args()
    args.repo=args.repo.resolve();args.data_dir=args.data_dir.resolve();args.output_dir=args.output_dir.resolve()
    if args.output_dir==args.data_dir or args.data_dir in args.output_dir.parents:
        p.error('Evidence must be outside source CSV directory')
    if args.mode!='csv' and not args.existing_project_endpoint:
        p.error('DB mode requires explicit existing project endpoint discovery assertion')
    args.output_dir.mkdir(parents=True,exist_ok=False)
    report={'started_utc':datetime.now(timezone.utc).isoformat(),'status':'in_progress',
        'scope':'full pinned Olist CSV oracle; optional existing-core read-only SELECT, no lifecycle',
        'code_commit':args.input_ref,'sql_commit':SQL_INPUT,'requirements_commit':REQUIREMENTS,
        'runner_sha256':file_sha(Path(__file__)),'database':{'status':'not_run'},
        'full_atomic_build_rebuild_rollback':'not_run','history_integration_rerun':'required_after_integration'}
    exit_code=1
    try:
        args.input_ref=subprocess.check_output(['git','-C',str(args.repo),'rev-parse',args.input_ref+'^{commit}'],text=True).strip()
        report['code_commit']=args.input_ref
        paths=['AGENTS.md','docs/phase-20261028/README.md','tests/model/input-manifest.lock.json',
            'hack-context/hackathon-students/docs/tasks.md','model/10_dims.sql','model/20_facts.sql','model/40_mart.sql',
            'model/50_answers.sql','model/55_answers_block_b.sql','answers/control.sql',
            *['docs/phase-20261028/experiments/'+x+'/results.json' for x in ('payments-prices','delivery-data','review-data')]]
        paths += ['answers/'+q+'.sql' for q in ('q01','q02','q03','q04','q04_window','q05')]
        paths += ['answers/q06-q10/'+q+'.sql' for q in ('q06','q07','q08','q09','q10','q10_coverage')]
        report['input_code_sha256']={path:sha(blob(args.repo,args.input_ref,path)) for path in paths}
        report['original_sql_sha256']={path:sha(blob(args.repo,SQL_INPUT,path)) for path in paths if path.startswith('answers/q06-q10/')}
        # Parsing the exact original SELECTs is done even with no DB available.
        for path in report['original_sql_sha256']:statements(blob(args.repo,SQL_INPUT,path).decode())
        entries=bind_inputs(args.repo,args.input_ref,args.data_dir)
        report['inputs']=entries
        print('Eight pinned CSV files verified; computing Q1–Q10 oracle',flush=True)
        oracle=Oracle(args.data_dir);q=oracle.answers()
        report['q1_q5_regression']=regression(q)
        report['published_oracle_comparisons']=published_comparisons(args.repo,args.input_ref,q)
        report['expected_core_fingerprints']={name:multiset(rows) for name,rows in oracle.core_expected()}
        (args.output_dir/'csv-oracle.json').write_bytes(encoded(q)+b'\n')
        report['csv_oracle_sha256']=file_sha(args.output_dir/'csv-oracle.json')
        report['oracle_row_counts']={k:len(v) for k,v in q.items()}
        if args.mode!='csv':
            ok=db_check(args,report,entries,oracle,q)
            report['status']='read_only_full_select_pass_lifecycle_pending' if ok else 'csv_pass_db_unavailable_or_identity_only'
            exit_code=0 if ok else 3
        else:
            report['status']='csv_pass_db_not_run';exit_code=0
        if any(file_sha(args.data_dir/e['file'])!=e['sha256'] for e in entries):
            raise ValueError('CSV changed during verification')
        report['csv_unchanged_after_run']=True
    except Exception as exc:
        report.update(status='fail',error_type=type(exc).__name__)
        # Do not persist arbitrary DB/server diagnostics or source row contents.
        report['error']=str(exc) if isinstance(exc,ValueError) else 'Unexpected runner failure; inspect controlled reproduction'
        exit_code=1
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat()
        (args.output_dir/'summary.json').write_bytes(encoded(report)+b'\n')
    print(json.dumps({'status':report['status'],'exit_code':exit_code,'evidence':str(args.output_dir)},ensure_ascii=False))
    return exit_code


if __name__=='__main__':
    sys.exit(main())
