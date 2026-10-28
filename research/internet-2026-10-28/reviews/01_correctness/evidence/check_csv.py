#!/usr/bin/env python3
"""R1 independent read-only aggregate check of the eight local CSVs; stdlib only."""
import csv, hashlib, json
from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal
P = Path(__file__).resolve().parents[5] / 'data'
F = ['olist_orders_dataset.csv','olist_order_items_dataset.csv','olist_order_payments_dataset.csv','olist_order_reviews_dataset.csv','olist_products_dataset.csv','olist_sellers_dataset.csv','olist_customers_dataset.csv','product_category_name_translation.csv']
files={}; tables={}
for name in F:
 p=P/name; sha=hashlib.sha256(); blob=hashlib.sha1(); blob.update(f'blob {p.stat().st_size}\0'.encode())
 with p.open('rb') as f:
  while b:=f.read(1048576): sha.update(b); blob.update(b)
 with p.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f); header=reader.fieldnames; rows=list(reader)
 tables[name]=rows; files[name]={'records':len(rows),'header':header,'sha256':sha.hexdigest(),'git_blob_sha1':blob.hexdigest(),'bytes':p.stat().st_size}
orders,items,pays,reviews,products,sellers,customers,translations=(tables[n] for n in F)
def keycheck(rows, cols):
 ks=[tuple(r[c] for c in cols) for r in rows]; return {'rows':len(ks),'distinct':len(set(ks)),'empty_key_rows':sum(any(not x for x in k) for k in ks)}
keys={'orders':keycheck(orders,['order_id']),'items':keycheck(items,['order_id','order_item_id']),'payments':keycheck(pays,['order_id','payment_sequential']),'reviews':keycheck(reviews,['review_id','order_id']),'products':keycheck(products,['product_id']),'sellers':keycheck(sellers,['seller_id']),'customers':keycheck(customers,['customer_id']),'translations':keycheck(translations,['product_category_name'])}
o={r['order_id']:r for r in orders}; c={r['customer_id']:r for r in customers}; prod={r['product_id'] for r in products}; sell={r['seller_id'] for r in sellers}
fi=defaultdict(Decimal); fp=defaultdict(Decimal); ic=Counter(); pc=Counter(); missing_money=Counter(); sr=defaultdict(Decimal); seller_orders=defaultdict(set); seller_dorders=defaultdict(set); delivered_price=Decimal(0)
for r in items:
 oid=r['order_id']; ic[oid]+=1
 for field in ('price','freight_value'):
  if not r[field]: missing_money['items.'+field]+=1
 if r['price'] and r['freight_value']: fi[oid]+=Decimal(r['price'])+Decimal(r['freight_value'])
 if oid in o:
  seller_orders[r['seller_id']].add(oid)
  if o[oid]['order_status']=='delivered':
   seller_dorders[r['seller_id']].add(oid); sr[r['seller_id']]+=Decimal(r['price']); delivered_price+=Decimal(r['price'])
for r in pays:
 oid=r['order_id']; pc[oid]+=1
 if not r['payment_value']:missing_money['payments.payment_value']+=1
 else:fp[oid]+=Decimal(r['payment_value'])
A=set(ic); B=set(pc); both=A&B; population=set(o); d={k:fp[k]-fi[k] for k in both}; nz=[v for v in d.values() if v != 0]; gt=[v for v in d.values() if abs(v)>Decimal('.01')]
fd=defaultdict(set); rid_orders=defaultdict(set); order_reviews=Counter(); pairs=set(); scores_by_id={}; score_pairs=Decimal(0)
for r in reviews:
 rid=r['review_id']; payload=tuple(r[k] for k in ('review_score','review_comment_title','review_comment_message','review_creation_date','review_answer_timestamp')); fd[rid].add(payload); rid_orders[rid].add(r['order_id']); order_reviews[r['order_id']]+=1; pairs.add((rid,r['order_id'])); score_pairs+=Decimal(r['review_score']); scores_by_id[rid]=Decimal(r['review_score'])
buyer_zips=defaultdict(set)
for r in customers:buyer_zips[r['customer_unique_id']].add(r['customer_zip_code_prefix'])
categories={r['product_category_name'] for r in products if r['product_category_name']}
translated={r['product_category_name'] for r in translations}
products_by_id={r['product_id']:r for r in products}
category_revenue=defaultdict(Decimal)
for r in items:
 if r['order_id'] in o and o[r['order_id']]['order_status']=='delivered':
  category_revenue[products_by_id[r['product_id']]['product_category_name']]+=Decimal(r['price'])
q1=[r for r in orders if '2016-09-01'<=r['order_purchase_timestamp']<'2018-09-01']; dv=[r for r in orders if r['order_status']=='delivered']; dids={r['order_id'] for r in dv}; best=max(sr,key=sr.get)
def mean(ids, amounts):
 ks=set(ids)&set(amounts); return {'n':len(ks),'sum':str(sum((amounts[k] for k in ks),Decimal(0))),'mean':str(sum((amounts[k] for k in ks),Decimal(0))/len(ks))}
result={'method':'R1 independent Python stdlib csv+Decimal; local bytes, no DB or Internet code execution','files':files,'total_records':sum(v['records'] for v in files.values()),'keys':keys,'fk_missing':{'orders_customer':sum(r['customer_id'] not in c for r in orders),'items_order':sum(r['order_id'] not in o for r in items),'items_product':sum(r['product_id'] not in prod for r in items),'items_seller':sum(r['seller_id'] not in sell for r in items),'payments_order':sum(r['order_id'] not in o for r in pays),'reviews_order':sum(r['order_id'] not in o for r in reviews)},'order_customer_cardinality':{'distinct_order_customer_ids':len({r['customer_id'] for r in orders}),'customers_unreferenced':len(set(c)-{r['customer_id'] for r in orders})},'money':{'missing_values':dict(missing_money),'all_orders':len(population),'both':len(both),'items_only':len(A-B),'payments_only':len(B-A),'neither':len(population-(A|B)),'items_only_sum':str(sum((fi[k] for k in A-B),Decimal(0))),'payments_only_sum':str(sum((fp[k] for k in B-A),Decimal(0))),'exact_nonzero_count':len(nz),'exact_delta_sum':str(sum(nz,Decimal(0))),'gt_cent_count':len(gt),'gt_cent_delta_sum':str(sum(gt,Decimal(0))),'all_abs_delta_sum':str(sum(map(abs,d.values()),Decimal(0))),'fanout_rows':sum(ic[k]*pc[k] for k in both),'item_correct':str(sum((fi[k] for k in both),Decimal(0))),'item_after_join':str(sum((fi[k]*pc[k] for k in both),Decimal(0))),'payment_correct':str(sum((fp[k] for k in both),Decimal(0))),'payment_after_join':str(sum((fp[k]*ic[k] for k in both),Decimal(0)))},'review':{'pairs':len(pairs),'ids':len(fd),'ids_multi_orders':sum(len(x)>1 for x in rid_orders.values()),'orders_multiple_rows':sum(n>1 for n in order_reviews.values()),'full_payload_conflicts':sum(len(x)>1 for x in fd.values()),'pair_weighted_mean':str(score_pairs/len(reviews)),'review_id_weighted_mean':str(sum(scores_by_id.values(),Decimal(0))/len(scores_by_id))},'customers':{'unique_buyers':len(buyer_zips),'multi_zip_prefix':sum(len(v)>1 for v in buyer_zips.values())},'categories':{'products_empty':sum(not r['product_category_name'] for r in products),'nonempty_distinct':len(categories),'missing_translations':sorted(categories-translated),'delivered_groups_including_empty':len(category_revenue),'delivered_price_total':str(sum(category_revenue.values(),Decimal(0))),'top_category':max(category_revenue,key=category_revenue.get),'top_category_price':str(max(category_revenue.values()))},'metrics':{'q1_all_orders':len(q1),'q1_delivered_orders':sum(r['order_status']=='delivered' for r in q1),'delivered_item_price':str(delivered_price),'top_seller':best,'top_seller_delivered_price':str(sr[best]),'top_seller_all_order_count':len(seller_orders[best]),'top_seller_delivered_order_count':len(seller_dorders[best]),'delivered_items_plus_freight':mean(dids,fi),'delivered_payment':mean(dids,fp),'all_items_plus_freight':mean(population,fi),'all_payment':mean(population,fp)},'time':{'no_nov_2016_orders':sum(r['order_purchase_timestamp'].startswith('2016-11') for r in orders),'sep_2018':sum(r['order_purchase_timestamp'].startswith('2018-09') for r in orders),'oct_2018':sum(r['order_purchase_timestamp'].startswith('2018-10') for r in orders),'tail_delivered':sum(r['order_status']=='delivered' and r['order_purchase_timestamp']>='2018-09-01' for r in orders),'max_purchase':max(r['order_purchase_timestamp'] for r in orders),'max_delivery':max(r['order_delivered_customer_date'] for r in orders)},'limits':['File-byte equality does not establish DB raw equality.','FD limited to decoded literal CSV payload; no inference for future data or SQL NULL.','No actual event time for each installment, extraction as-of or causes established.']}
print(json.dumps(result,ensure_ascii=False,indent=2))
