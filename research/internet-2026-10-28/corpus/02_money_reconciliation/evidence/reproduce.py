#!/usr/bin/env python3
"""Streaming public pinned CSV; no datasets saved. Python stdlib, Decimal amounts."""
import csv, hashlib, json, urllib.request
from collections import Counter, defaultdict
from decimal import Decimal as D
REF='d9e49802f3e92d09ee94ab9ccc5e457f207a8959'
BASE=f'https://raw.githubusercontent.com/olist/work-at-olist-data/{REF}/datasets/'
meta={}
def rows(name):
    h=hashlib.sha256(); count=0
    with urllib.request.urlopen(BASE+name, timeout=60) as response:
        def lines():
            for b in response:
                h.update(b)
                yield b.decode('utf-8-sig')
        reader=csv.DictReader(lines()); header=reader.fieldnames
        for row in reader:
            count+=1; yield row
    meta[name]={'url':BASE+name,'sha256':h.hexdigest(),'header':header,'rows':count}
orders={}; items=defaultdict(lambda:[0,D(0),D(0),0]); payments=defaultdict(lambda:[0,D(0),0]); sellers=defaultdict(lambda:defaultdict(set)); nulls=Counter(); zeros=Counter(); installments=Counter()
for r in rows('olist_orders_dataset.csv'):
    assert r['order_id'] not in orders
    orders[r['order_id']]=(r['order_status'],r['order_purchase_timestamp'])
for r in rows('olist_order_items_dataset.csv'):
    x=items[r['order_id']]; x[0]+=1
    for col,idx in [('price',1),('freight_value',2)]:
        if r[col]=='': nulls[col]+=1; x[3]+=1
        else:
            v=D(r[col]); x[idx]+=v; zeros[col]+=v==0
    sellers[r['seller_id']][r['order_id']].add(r['order_item_id'])
for r in rows('olist_order_payments_dataset.csv'):
    x=payments[r['order_id']]; x[0]+=1
    if r['payment_value']=='': nulls['payment_value']+=1; x[2]+=1
    else:
        v=D(r['payment_value']); x[1]+=v; zeros['payment_value']+=v==0
    installments[r['payment_installments']]+=1
assert set(items)<=set(orders) and set(payments)<=set(orders)
def group(ids):
    ids=list(ids); both=[i for i in ids if i in items and i in payments]; valid=[i for i in both if not items[i][3] and not payments[i][2]]
    deltas=[payments[i][1]-items[i][1]-items[i][2] for i in valid]
    def avg(values): return str(sum(values,D(0))/len(values)) if values else None
    return {'orders':len(ids),'both':len(both),'items_only':sum(i in items and i not in payments for i in ids),'payments_only':sum(i in payments and i not in items for i in ids),'neither':sum(i not in items and i not in payments for i in ids),'comparable_no_null':len(valid),'positive':sum(d>0 for d in deltas),'negative':sum(d<0 for d in deltas),'equal':sum(d==0 for d in deltas),'mismatch':sum(d!=0 for d in deltas),'delta_sum':str(sum(deltas,D(0))),'abs_delta_sum':str(sum(map(abs,deltas),D(0))),'over_0_01':sum(abs(d)>D('.01') for d in deltas),'over_0_01_delta_sum':str(sum((d for d in deltas if abs(d)>D('.01')),D(0))),'over_0_01_positive':sum(d>D('.01') for d in deltas),'over_0_01_negative':sum(d< -D('.01') for d in deltas), 'payments_only_sum':str(sum((payments[i][1] for i in ids if i in payments and i not in items),D(0))), 'items_only_sum':str(sum((items[i][1]+items[i][2] for i in ids if i in items and i not in payments),D(0))), 'items_present_count':sum(i in items and not items[i][3] for i in ids), 'payment_present_count':sum(i in payments and not payments[i][2] for i in ids),'over_0_10':sum(abs(d)>D('.10') for d in deltas),'price_sum_both':str(sum((items[i][1] for i in valid),D(0))),'freight_sum_both':str(sum((items[i][2] for i in valid),D(0))),'payment_sum_both':str(sum((payments[i][1] for i in valid),D(0))),'items_plus_freight_avg_present':avg([items[i][1]+items[i][2] for i in ids if i in items and not items[i][3]]),'price_avg_present':avg([items[i][1] for i in ids if i in items and not items[i][3]]),'payment_avg_present':avg([payments[i][1] for i in ids if i in payments and not payments[i][2]]),'fanout_join_rows':sum(items[i][0]*payments[i][0] for i in both),'fanout_item_sum':str(sum(((items[i][1]+items[i][2])*payments[i][0] for i in valid),D(0))),'fanout_payment_sum':str(sum((payments[i][1]*items[i][0] for i in valid),D(0))),'orders_multi_both':sum(items[i][0]>1 and payments[i][0]>1 for i in both)}
rank=defaultdict(D)
# aggregate seller revenue separately, reread stream to avoid keeping item rows
for r in rows('olist_order_items_dataset.csv'):
    if orders[r['order_id']][0]=='delivered': rank[r['seller_id']]+=D(r['price'])
top=max(rank,key=rank.get)
period={i for i,(s,t) in orders.items() if '2016-09'<=t[:7]<='2018-08'}
result={'ref':REF,'metadata':meta,'nulls':dict(nulls),'zero_values':dict(zeros),'installment_counts':dict(installments),'all':group(orders),'delivered':group(i for i in orders if orders[i][0]=='delivered'),'q1_period_all':group(period),'q1_period_delivered':group(i for i in period if orders[i][0]=='delivered'),'top_seller':{'id':top,'delivered_price':str(rank[top]),'order_count_all':len(sellers[top]),'order_count_delivered':sum(orders[i][0]=='delivered' for i in sellers[top])}}
print(json.dumps(result,indent=2,sort_keys=True))
