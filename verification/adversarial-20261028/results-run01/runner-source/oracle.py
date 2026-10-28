"""Small Python oracle over fixture dictionaries, compared with executed SQL.

Only documented named policies are asserted. No Olist control totals are used.
"""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal


def number(v):
    return None if v is None else Decimal(v)


def date(v):
    return None if v is None else datetime.fromisoformat(v)


def mean(values):
    known = [x for x in values if x is not None]
    return sum(known, Decimal(0)) / len(known) if known else None


def complete_sum(values):
    return sum(values, Decimal(0)) if values and all(x is not None for x in values) else None


def measurement(order, basis):
    purchase = date(order.get('order_purchase_timestamp'))
    actual = date(order.get('order_delivered_customer_date'))
    estimate = date(order.get('order_estimated_delivery_date'))
    duration = late = None
    if order['order_status'] == 'delivered':
        if purchase is not None and actual is not None and actual >= purchase:
            delta = actual - purchase
            duration = Decimal(delta.days) + Decimal(delta.seconds) / 86400 + Decimal(delta.microseconds) / 86400000000
        if actual is not None and estimate is not None:
            late = actual.date() > estimate.date() if basis == 'calendar_day' else actual > estimate
    return duration, late


def delivery_aggregate(orders, basis):
    values = [measurement(o, basis) for o in orders]
    durations = [d for d, _ in values if d is not None]
    late = [l for _, l in values if l is not None]
    return dict(orders_count=len(orders), duration_denominator=len(durations),
                avg_delivery_days=mean(durations), late_denominator=len(late),
                late_orders=sum(late), late_pct=Decimal(100) * sum(late) / len(late) if late else None)


def expected(t):
    result = {}
    orders = {o['order_id']: o for o in t['orders']}
    customers = {c['customer_id']: c for c in t['customers']}
    products = {p['product_id']: p for p in t['products']}
    items = defaultdict(list); payments = defaultdict(list); reviews = defaultdict(list)
    for name, target in [('order_items', items), ('order_payments', payments), ('order_reviews', reviews)]:
        for row in t[name]:
            target[row['order_id']].append(row)
    delivered = [o for o in orders.values() if o['order_status'] == 'delivered']
    vo = []
    for oid, o in orders.items():
        its, pays, revs = items[oid], payments[oid], reviews[oid]
        prices = [number(i['price']) for i in its]
        freights = [number(i['freight_value']) for i in its]
        gmvs = [number(i['price']) + number(i['freight_value'])
                if i['price'] is not None and i['freight_value'] is not None else None for i in its]
        vo.append(dict(order_id=oid, source_rows_count=len(its), payments_count=len(pays),
                       review_pairs_count=len(revs), price_valid_count=sum(p is not None for p in prices),
                       item_revenue=complete_sum(prices), freight_amount=complete_sum(freights),
                       order_gmv=complete_sum(gmvs), payment_amount=complete_sum([number(p['payment_value']) for p in pays]),
                       payment_coverage='both' if its and pays else 'items_only' if its else 'payments_only' if pays else 'neither',
                       customer_unique_id=customers[o['customer_id']]['customer_unique_id']))
    result['orders'] = vo
    result['facts'] = [dict(orders=len(orders), items=len(t['order_items']),
                            payments=len(t['order_payments']), reviews=len(t['order_reviews']))]
    result['reviews'] = [dict(r, review_score=int(r['review_score']) if r['review_score'] is not None else None)
                         for r in t['order_reviews']]
    by_id = defaultdict(list)
    for row in t['order_reviews']:
        by_id[row['review_id']].append(row)
    result['review_conflicts'] = []
    for rid, rows in by_id.items():
        variants = {tuple((k, v) for k, v in r.items() if k != 'order_id') for r in rows}
        result['review_conflicts'].append(dict(review_id=rid, payload_variant_count=len(variants),
                                               association_count=len(rows), has_payload_conflict=len(variants) > 1,
                                               review_score=None if len(variants) > 1 or rows[0]['review_score'] is None
                                               else int(rows[0]['review_score'])))
    result['delivery'] = [dict(order_id=o['order_id'],
                               purchase_to_delivery_days=measurement(o, 'timestamp')[0],
                               is_late_calendar_day=measurement(o, 'calendar_day')[1],
                               is_late_timestamp=measurement(o, 'timestamp')[1]) for o in orders.values()]
    q1 = []
    for offset in range(24):
        year, month = 2016 + (8 + offset) // 12, (8 + offset) % 12 + 1
        month_orders = [o for o in orders.values() if (date(o['order_purchase_timestamp']) is not None and
                        (date(o['order_purchase_timestamp']).year, date(o['order_purchase_timestamp']).month) == (year, month))]
        eligible = [o for o in month_orders if o['order_status'] == 'delivered']
        values = [next(v['item_revenue'] for v in vo if v['order_id'] == o['order_id']) for o in eligible]
        revenue = complete_sum(values) if eligible else Decimal(0)
        q1.append(dict(month_start=f'{year:04}-{month:02}-01', orders_placed=len(month_orders),
                       orders_delivered=len(eligible), item_revenue=revenue))
    result['q1'] = q1
    seller_rows = []
    for s in t['sellers']:
        its = [i for i in t['order_items'] if i['seller_id'] == s['seller_id']]
        if not its:
            continue
        eligible = [i for i in its if orders[i['order_id']]['order_status'] == 'delivered']
        seller_rows.append(dict(seller_id=s['seller_id'],
                                orders_all_statuses=len({i['order_id'] for i in its}), units_all_statuses=len(its),
                                orders_delivered=len({i['order_id'] for i in eligible}), units_delivered=len(eligible),
                                item_revenue=complete_sum([number(i['price']) for i in eligible]) if eligible else Decimal(0)))
    result['q2'] = seller_rows
    delivered_vo = [v for v in vo if orders[v['order_id']]['order_status'] == 'delivered']
    result['q3'] = [dict(n_delivered_orders=len(delivered_vo),
                         n_order_gmv=sum(v['order_gmv'] is not None for v in delivered_vo),
                         n_payment_amount=sum(v['payment_amount'] is not None for v in delivered_vo),
                         avg_order_gmv=mean([v['order_gmv'] for v in delivered_vo]),
                         avg_payment_amount=mean([v['payment_amount'] for v in delivered_vo]),
                         avg_source_rows=mean([Decimal(v['source_rows_count']) for v in delivered_vo]))]
    buyers = defaultdict(int)
    for o in orders.values():
        buyers[customers[o['customer_id']]['customer_unique_id']] += 1
    result['q4'] = [dict(buyers=len(buyers), repeat_buyers=sum(n > 1 for n in buyers.values()),
                         repeat_buyer_pct=Decimal(100) * sum(n > 1 for n in buyers.values()) / len(buyers))]
    categories = {None} | {p['product_category_name'] for p in t['products']} | {
        p['product_category_name'] for p in t['product_category_translation']}
    translations = {p['product_category_name']: p['product_category_name_english'] for p in t['product_category_translation']}
    category_rows = []
    for category in categories:
        its = [i for i in t['order_items'] if orders[i['order_id']]['order_status'] == 'delivered' and
               products[i['product_id']]['product_category_name'] == category]
        category_rows.append(dict(category_key='unknown' if category is None else 'pt:' + category,
                                  is_unknown=category is None, is_translated=translations.get(category) is not None,
                                  revenue_item_rows_count=len(its),
                                  item_revenue=complete_sum([number(i['price']) for i in its]) if its else Decimal(0)))
    total = complete_sum([r['item_revenue'] for r in category_rows])
    for row in category_rows:
        row['total_item_revenue'] = total
        row['revenue_pct'] = Decimal(100) * row['item_revenue'] / total if row['item_revenue'] is not None and total else None
    result['q5'] = category_rows
    result['q6'] = []; result['q7'] = []; result['q10'] = []; result['q10_coverage'] = []
    for population in ('all_statuses', 'delivered'):
        pop_orders = list(orders.values()) if population == 'all_statuses' else delivered
        pop_ids = {o['order_id'] for o in pop_orders}
        pop_items = [i for i in t['order_items'] if i['order_id'] in pop_ids]
        pitems = defaultdict(list)
        for i in pop_items:
            pitems[i['product_id']].append(i)
        price_counts = {p: len({number(i['price']) for i in its if i['price'] is not None}) for p, its in pitems.items()}
        max_count = max(price_counts.values(), default=0)
        for product, its in pitems.items():
            if price_counts[product] != max_count or max_count == 0:
                continue
            groups = defaultdict(int)
            for i in its:
                purchased = date(orders[i['order_id']]['order_purchase_timestamp'])
                groups[purchased.date().isoformat() if purchased else None, number(i['price'])] += 1
            for (day, price), units in groups.items():
                result['q6'].append(dict(population=population, product_id=product, distinct_prices=max_count,
                                         units_with_unknown_price=sum(i['price'] is None for i in its),
                                         purchase_date=day, price=price, units_sold=units))
        states = defaultdict(list)
        for o in pop_orders:
            states[customers[o['customer_id']]['customer_state']].append(o)
        for state, state_orders in states.items():
            for basis in ('calendar_day', 'timestamp'):
                result['q7'].append(dict(population=population, customer_state=state, late_basis=basis,
                                         **delivery_aggregate(state_orders, basis)))
        scores = {o['order_id']: {int(r['review_score']) for r in reviews[o['order_id']] if r['review_score'] is not None}
                  for o in pop_orders}
        result['q10_coverage'].append(dict(population=population, orders_count=len(pop_orders),
                                           orders_without_score=sum(not s for s in scores.values()),
                                           orders_with_multiple_scores=sum(len(s) > 1 for s in scores.values()),
                                           orders_in_multiple_valid_score_groups=sum(len(s & {1, 2, 3, 4, 5}) > 1 for s in scores.values()),
                                           orders_with_out_of_range_score=sum(bool(s - {1, 2, 3, 4, 5}) for s in scores.values())))
        for policy in ('within_score', 'single_score_only'):
            for score in range(1, 6):
                group = [o for o in pop_orders if score in scores[o['order_id']] and
                         (policy == 'within_score' or len(scores[o['order_id']]) == 1)]
                for basis in ('calendar_day', 'timestamp'):
                    result['q10'].append(dict(population=population, score_policy=policy, review_score=score,
                                              late_basis=basis, **delivery_aggregate(group, basis)))
    status_orders = defaultdict(list)
    for o in orders.values():
        status_orders[o['order_status']].append(o)
    result['q8'] = [dict(order_status=status, orders_count=len(group),
                         orders_pct=Decimal(100) * len(group) / len(orders),
                         orders_without_items=sum(not items[o['order_id']] for o in group))
                    for status, group in status_orders.items()]
    result['q9'] = []; result['q9_methods'] = []
    def in_year(p):
        purchased = date(orders[p['order_id']]['order_purchase_timestamp'])
        return purchased is not None and purchased.year == 2018
    state_payments = defaultdict(list)
    for p in t['order_payments']:
        if in_year(p):
            state_payments[customers[orders[p['order_id']]['customer_id']]['customer_state']].append(p)
    for state, ps in state_payments.items():
        amounts = [number(p['payment_value']) for p in ps]
        cc = [number(p['payment_installments']) for p in ps if p['payment_type'] == 'credit_card']
        parts = [number(p['payment_installments']) for p in ps]
        result['q9'].append(dict(customer_state=state, payment_count=len(ps),
                                 amount_denominator=sum(v is not None for v in amounts), payment_amount=complete_sum(amounts),
                                 known_payment_amount_sum=sum((v for v in amounts if v is not None), Decimal(0)) if any(v is not None for v in amounts) else None,
                                 installments_denominator=sum(v is not None for v in parts), avg_installments_all_types=mean(parts),
                                 credit_installments_denominator=sum(v is not None for v in cc), avg_installments_credit_card=mean(cc)))
    for period in ('all_snapshot', 'purchase_2018'):
        grouped = defaultdict(list)
        for p in t['order_payments']:
            if period == 'all_snapshot' or in_year(p):
                grouped[p['payment_type']].append(p)
        for kind, ps in grouped.items():
            parts = [number(p['payment_installments']) for p in ps]
            result['q9_methods'].append(dict(period=period, payment_type=kind, payment_count=len(ps),
                                             installments_denominator=sum(v is not None for v in parts), avg_installments=mean(parts)))
    return result


QUERIES = {
    'facts': "SELECT (SELECT count(*) FROM core.fact_order) AS orders, (SELECT count(*) FROM core.fact_order_item) AS items, (SELECT count(*) FROM core.fact_payment) AS payments, (SELECT count(*) FROM core.fact_review) AS reviews",
    'orders': 'SELECT * FROM mart.v_orders',
    'reviews': "SELECT review_id,order_id,review_score,review_comment_title,review_comment_message,to_char(review_creation_date,'YYYY-MM-DD HH24:MI:SS') AS review_creation_date,to_char(review_answer_timestamp,'YYYY-MM-DD HH24:MI:SS') AS review_answer_timestamp FROM core.fact_review",
    'review_conflicts': 'SELECT * FROM mart.v_review',
    'delivery': 'SELECT * FROM mart.v_order_delivery_variants',
    'q1': 'SELECT * FROM mart.q01_revenue_monthly', 'q2': 'SELECT * FROM mart.q02_sellers_top10',
    'q3': 'SELECT * FROM mart.q03_average_order', 'q4': 'SELECT * FROM mart.q04_buyers_repeat',
    'q5': 'SELECT * FROM mart.q05_category_revenue', 'q6': 'SELECT * FROM mart.q06_price_history',
    'q7': 'SELECT * FROM mart.q07_delivery_by_state', 'q8': 'SELECT * FROM mart.q08_status_snapshot',
    'q9': 'SELECT * FROM mart.q09_payments_2018_by_state', 'q9_methods': 'SELECT * FROM mart.q09_payment_methods',
    'q10': 'SELECT * FROM mart.q10_review_delivery', 'q10_coverage': 'SELECT * FROM mart.q10_review_coverage'}


KEYS = {'facts': (), 'orders': ('order_id',), 'reviews': ('review_id', 'order_id'),
        'review_conflicts': ('review_id',), 'delivery': ('order_id',), 'q1': ('month_start',),
        'q2': ('seller_id',), 'q3': (), 'q4': (), 'q5': ('category_key',),
        'q6': ('population', 'product_id', 'purchase_date', 'price'),
        'q7': ('population', 'customer_state', 'late_basis'), 'q8': ('order_status',),
        'q9': ('customer_state',), 'q9_methods': ('period', 'payment_type'),
        'q10': ('population', 'score_policy', 'late_basis', 'review_score'), 'q10_coverage': ('population',)}


def compare(label, actual, expected_rows, keys):
    key = lambda row: tuple(row[k] for k in keys)
    a = {key(row): row for row in actual}; e = {key(row): row for row in expected_rows}
    if len(a) != len(actual) or len(e) != len(expected_rows):
        raise AssertionError(f'{label}: duplicate result keys')
    if a.keys() != e.keys():
        raise AssertionError(f'{label}: key sets differ; missing={e.keys()-a.keys()}, extra={a.keys()-e.keys()}')
    comparisons = 0
    for k, row in e.items():
        for column, expected_value in row.items():
            actual_value = a[k][column]
            equal = actual_value == expected_value
            if isinstance(expected_value, Decimal) and isinstance(actual_value, (Decimal, int)):
                equal = abs(actual_value - expected_value) < Decimal('1e-12')
            if not equal:
                raise AssertionError(f'{label}{k}.{column}: actual={actual_value!r}, expected={expected_value!r}')
            comparisons += 1
    return comparisons
