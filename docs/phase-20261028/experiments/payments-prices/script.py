#!/usr/bin/env python3
"""CSV-only Q6/Q9 experiment. Run from repository root with Python 3 stdlib."""
import csv, hashlib, json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

root = Path(__file__).resolve().parents[4]
data = root / 'data'
out = Path(__file__).with_name('results.json')
expected = {
 'olist_orders_dataset.csv':'8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf',
 'olist_order_items_dataset.csv':'4f6abdbbc94036d0df4a76fa0520c072e31a40119d70f7f370fba1e2285d2bcb',
 'olist_order_payments_dataset.csv':'61674868ed7b872aac3dcd95bf774448a88f6426b183f21be55f75af021ffdec',
 'olist_customers_dataset.csv':'c26c17f59f3027a6a0dbeb8f1fa373c38f3323ecc84f225a8f4820e5bb288df8',
}
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''): h.update(block)
    return h.hexdigest()
def rows(name):
    with (data/name).open(newline='', encoding='utf-8-sig') as f:
        yield from csv.DictReader(f)
def money(s): return int(Decimal(s)*100) if s else None
def period(date): return bool(date and '2018-01-01' <= date[:10] < '2019-01-01')
def group(): return {'payment_rows':0, 'amount_cents':0, 'known_amount_count':0, 'missing_amount_count':0, 'zero_amount_count':0, 'installments_sum':0, 'installments_count':0, 'missing_installments_count':0, 'zero_installments_count':0, 'credit_installments_sum':0, 'credit_installments_count':0, 'order_ids':set()}
def add(g, p):
    g['payment_rows']+=1; g['order_ids'].add(p['order_id'])
    amount=money(p['payment_value']); ins=int(p['payment_installments']) if p['payment_installments'] else None
    if amount is None: g['missing_amount_count']+=1
    else:
        g['known_amount_count']+=1; g['amount_cents']+=amount; g['zero_amount_count']+=amount==0
    if ins is None: g['missing_installments_count']+=1
    else:
        g['installments_count']+=1; g['installments_sum']+=ins; g['zero_installments_count']+=ins==0
        if p['payment_type']=='credit_card': g['credit_installments_count']+=1; g['credit_installments_sum']+=ins
def finish(g):
    g=dict(g); g['orders']=len(g.pop('order_ids'))
    for label, numerator, denominator in [('avg_installments_all_types','installments_sum','installments_count'),('avg_installments_credit_card','credit_installments_sum','credit_installments_count')]:
        g[label]=round(g[numerator]/g[denominator],6) if g[denominator] else None
    return g
hashes={name:{'sha256':digest(data/name),'baseline_sha256':sha,'match':digest(data/name)==sha} for name,sha in expected.items()}
if not all(v['match'] for v in hashes.values()): raise SystemExit('CSV baseline hash mismatch: stop')
customers={}
for c in rows('olist_customers_dataset.csv'):
    assert c['customer_id'] not in customers
    customers[c['customer_id']]=c['customer_state']
orders={}
for o in rows('olist_orders_dataset.csv'):
    assert o['order_id'] not in orders and o['customer_id'] in customers
    if o['order_purchase_timestamp']:
        datetime.strptime(o['order_purchase_timestamp'], '%Y-%m-%d %H:%M:%S')
    orders[o['order_id']]={'status':o['order_status'], 'date':o['order_purchase_timestamp'], 'state':customers[o['customer_id']]}
pg=defaultdict(group); by_order=Counter(); payment_types_by_order=defaultdict(set); unmatched_payments=0
for p in rows('olist_order_payments_dataset.csv'):
    o=orders.get(p['order_id'])
    if o is None: unmatched_payments+=1; continue
    by_order[p['order_id']]+=1; payment_types_by_order[p['order_id']].add(p['payment_type'])
    for pop in (['all_statuses','delivered'] if o['status']=='delivered' else ['all_statuses']):
        for window in (['all_snapshot','purchase_2018'] if period(o['date']) else ['all_snapshot']):
            for dimension, key in [('total','ALL'),('type',p['payment_type'] or '<missing>'),('state',o['state'] or '<missing>')]: add(pg[(pop,window,dimension,key)],p)
unknown_payment_dates=sum(n for oid,n in by_order.items() if not orders[oid]['date'])
missing_orders=[oid for oid in orders if oid not in by_order]
split={}
for pop in ('all_statuses','delivered'):
    for window in ('all_snapshot','purchase_2018'):
        eligible=[oid for oid in orders if (pop=='all_statuses' or orders[oid]['status']=='delivered') and (window=='all_snapshot' or period(orders[oid]['date']))]
        split[pop+'/'+window]={'orders':len(eligible),'orders_without_payment':sum(oid not in by_order for oid in eligible),'orders_with_multiple_payment_rows':sum(by_order[oid]>1 for oid in eligible),'payment_rows_in_multirow_orders':sum(by_order[oid] for oid in eligible if by_order[oid]>1),'orders_with_multiple_payment_types':sum(len(payment_types_by_order[oid])>1 for oid in eligible)}
prices={pop:defaultdict(set) for pop in ('all_statuses','delivered')}; item_rows=Counter(); unmatched_items=0; missing_item_dates=Counter(); missing_prices=Counter()
for i in rows('olist_order_items_dataset.csv'):
    o=orders.get(i['order_id'])
    if o is None: unmatched_items+=1; continue
    for pop in (['all_statuses','delivered'] if o['status']=='delivered' else ['all_statuses']):
        item_rows[pop]+=1; missing_item_dates[pop]+=not bool(o['date']); missing_prices[pop]+=not bool(i['price'])
        if i['price']: prices[pop][i['product_id']].add(money(i['price']))
winners={}
for pop, products in prices.items():
    maximum=max(map(len,products.values()),default=0)
    leaders=sorted(product for product, vals in products.items() if len(vals)==maximum)
    ranked=sorted(((len(v),k) for k,v in products.items()), key=lambda x:(-x[0],x[1]))[:10]
    winners[pop]={'max_distinct_prices':maximum,'product_ids':leaders,'top_10':[{'product_id':k,'distinct_prices':n} for n,k in ranked]}
# Re-read stream: detailed winner histories retain day, price, seller; no item x payment join.
history=Counter(); sellers=defaultdict(set); dayprices=defaultdict(set); daysellers=defaultdict(set); winner_status=Counter()
for i in rows('olist_order_items_dataset.csv'):
    o=orders.get(i['order_id'])
    if not o: continue
    for pop in (['all_statuses','delivered'] if o['status']=='delivered' else ['all_statuses']):
        product=i['product_id']
        if product not in winners[pop]['product_ids']: continue
        date=o['date'][:10] if o['date'] else None; price=i['price'] or None; seller=i['seller_id'] or None
        history[(pop,product,date,price,seller)]+=1
        sellers[(pop,product)].add(seller); dayprices[(pop,product,date)].add(price); daysellers[(pop,product,date)].add(seller)
        winner_status[(pop,product,o['status'])]+=1
hist=[{'population':p,'product_id':prod,'purchase_date':date,'price':price,'seller_id':seller,'units':count} for (p,prod,date,price,seller),count in sorted(history.items(),key=lambda x:tuple(str(y) for y in x[0]))]
for pop,w in winners.items():
    w['winner_detail']={product:{'sellers':len(sellers[(pop,product)]),'days_observed':sum(k[:2]==(pop,product) for k in dayprices),'days_with_multiple_prices':sum(k[:2]==(pop,product) and len(v)>1 for k,v in dayprices.items()),'days_with_multiple_sellers':sum(k[:2]==(pop,product) and len(v)>1 for k,v in daysellers.items()),'statuses':{status:n for (p,pr,status),n in winner_status.items() if p==pop and pr==product},'units':sum(row['units'] for row in hist if row['population']==pop and row['product_id']==product),'examples_multiple_price_days':[{'date':k[2],'prices':sorted(v,key=str),'seller_count':len(daysellers[k])} for k,v in sorted(dayprices.items(),key=lambda kv:str(kv[0])) if k[:2]==(pop,product) and len(v)>1][:5]} for product in w['product_ids']}
for pop in ('all_statuses', 'delivered'):
    for window in ('all_snapshot', 'purchase_2018'):
        total = pg[(pop,window,'total','ALL')]
        for dim in ('state','type'):
            parts = [g for (p,w,d,k),g in pg.items() if (p,w,d)==(pop,window,dim)]
            for field in ('payment_rows','amount_cents','known_amount_count','missing_amount_count','installments_sum','installments_count','credit_installments_count'):
                assert sum(g[field] for g in parts) == total[field], (pop,window,dim,field)
        assert total['payment_rows'] == sum(by_order[oid] for oid in total['order_ids'])
    assert item_rows[pop] >= sum(winner_status[(pop,prod,status)] for prod in winners[pop]['product_ids'] for status in ('delivered','shipped','canceled','unavailable','invoiced','processing','created','approved'))
result={'input_baseline':{'repository_commit':'bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4','manifest':'answers/baseline-manifest.json','files':hashes},'rows':{'orders':len(orders),'customers':len(customers),'items_by_population':dict(item_rows),'unmatched_items':unmatched_items,'unmatched_payments':unmatched_payments,'missing_purchase_dates_orders':sum(not o['date'] for o in orders.values()),'payment_rows_with_unknown_purchase_date':unknown_payment_dates,'missing_price_items':dict(missing_prices),'missing_purchase_dates_items':dict(missing_item_dates)},'q9':{'aggregates':[dict(population=p,period=w,dimension=d,key=k,**finish(g)) for (p,w,d,k),g in sorted(pg.items())], 'split_and_missing_orders':split, 'orders_without_payment_ids':missing_orders},'q6':{'winners':winners,'winner_history_by_seller_day_price':hist},'notes':['CSV-only, no core execution','purchase_2018 uses order purchase timestamp; all_snapshot includes unknown purchase dates','each payment row counted once; sums in integer cents','units are item rows, not confirmed final sale for non-delivered orders']}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(f'Wrote {out}; hashes matched; Q6 winner history rows {len(hist)}')
