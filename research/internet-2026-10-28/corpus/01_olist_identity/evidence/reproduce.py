#!/usr/bin/env python3
"""Read only four local CSVs; emit aggregates, no review texts. Run from repo root."""
import csv, hashlib, json, collections, pathlib, sys
root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'data')
names=['olist_customers_dataset.csv','olist_order_reviews_dataset.csv','olist_products_dataset.csv','product_category_name_translation.csv']
result={'method':'UTF-8-sig csv.DictReader; exact decoded field equality including empty string; counts are CSV records not physical lines','files':{}}
for n in names:
 p=root/n; sha=hashlib.sha256(); git=hashlib.sha1(); git.update(('blob %d\0'%p.stat().st_size).encode())
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): sha.update(chunk); git.update(chunk)
 with p.open(encoding='utf-8-sig',newline='') as f:
  reader=csv.DictReader(f); header=reader.fieldnames; count=sum(1 for _ in reader)
 result['files'][n]={'sha256':sha.hexdigest(),'git_blob_sha1':git.hexdigest(),'bytes':p.stat().st_size,'header':header,'records':count}
def records(n):
 with (root/n).open(encoding='utf-8-sig',newline='') as f:
  yield from csv.DictReader(f)
ci=collections.Counter(); cu=collections.defaultdict(set); empty_customer=empty_unique=0
for x in records(names[0]):
 ci[x['customer_id']]+=1; cu[x['customer_unique_id']].add(x['customer_zip_code_prefix']); empty_customer+=not x['customer_id']; empty_unique+=not x['customer_unique_id']
result['customers']={'customer_id_distinct':len(ci),'duplicate_customer_id_groups':sum(n>1 for n in ci.values()),'empty_customer_ids':empty_customer,'unique_id_distinct':len(cu),'empty_unique_ids':empty_unique,'unique_ids_multiple_zip_prefixes':sum(len(z)>1 for z in cu.values())}
fields=['review_score','review_comment_title','review_comment_message','review_creation_date','review_answer_timestamp']; groups=collections.defaultdict(list); pairs=collections.Counter(); orders=collections.Counter()
empty_keys=0
for x in records(names[1]):
 empty_keys+=not x['review_id'] or not x['order_id']; groups[x['review_id']].append(x); pairs[(x['review_id'],x['order_id'])]+=1; orders[x['order_id']]+=1
conf={f:sum(len({x[f] for x in g})>1 for g in groups.values()) for f in fields}; examples=[]
for ident,g in sorted(groups.items()):
 changes=[f for f in fields if len({x[f] for x in g})>1]
 if changes and len(examples)<3:
  examples.append({'review_id':ident,'order_ids':[x['order_id'] for x in g],'differing_fields':changes,'payload_sha256':[hashlib.sha256(json.dumps([x[f] for f in fields],ensure_ascii=False,separators=(',',':')).encode()).hexdigest() for x in g]})
repeat_examples=[{'review_id':ident,'order_ids':[x['order_id'] for x in g], 'payload_sha256':hashlib.sha256(json.dumps([g[0][f] for f in fields],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()} for ident,g in sorted(groups.items()) if len(g)>1][:3]
result['reviews']={'repeat_examples':repeat_examples,'review_id_distinct':len(groups),'review_id_multiple_rows':sum(len(g)>1 for g in groups.values()),'review_id_multiple_orders':sum(len({x['order_id'] for x in g})>1 for g in groups.values()),'order_id_multiple_reviews':sum(n>1 for n in orders.values()),'pair_distinct':len(pairs),'duplicate_pair_groups':sum(n>1 for n in pairs.values()),'empty_key_rows':empty_keys,'conflicting_ids_by_field':conf,'conflicting_ids_any_payload':sum(len({tuple(x[f] for f in fields) for x in g})>1 for g in groups.values()),'conflicting_examples':examples}
pc=collections.Counter(); tc=collections.Counter(); cats=set(); missing=0
for x in records(names[2]):
 pc[x['product_id']]+=1; missing+=not x['product_category_name']; cats.add(x['product_category_name']) if x['product_category_name'] else None
for x in records(names[3]): tc[x['product_category_name']]+=1
result['categories']={'product_ids_distinct':len(pc),'duplicate_product_id_groups':sum(v>1 for v in pc.values()),'missing_category_products':missing,'nonempty_product_categories':len(cats),'translation_key_duplicate_groups':sum(v>1 for v in tc.values()),'translation_keys':len(tc),'untranslated_product_categories':sorted(cats-set(tc))}
print(json.dumps(result,ensure_ascii=False,indent=2))
