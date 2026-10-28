#!/usr/bin/env python3
"""Retrieve small source documents and log compact results only; never execute fetched content."""
import urllib.request, json, hashlib, datetime
from pathlib import Path
O=Path(__file__).resolve().parent.parent
csvdata=json.loads((O/'evidence/csv-check.json').read_text())
base='https://raw.githubusercontent.com/daniilivanovp-droid/hackathon-students/3da32d149bfa14dca3fdb0c5863d0771c38efbfc/'
sources=[('olist_tree','https://api.github.com/repos/olist/work-at-olist-data/contents/datasets?ref=d9e49802f3e92d09ee94ab9ccc5e457f207a8959'),('kaggle_metadata','https://www.kaggle.com/api/v1/datasets/view/olistbr/brazilian-ecommerce'),('organizer_repo','https://api.github.com/repos/daniilivanovp-droid/hackathon-students'),('organizer_head','https://api.github.com/repos/daniilivanovp-droid/hackathon-students/commits/main')]+[(f'organizer_{x}',base+x) for x in ('README.md','docs/handout.md','docs/tasks.md')]+[('olist_license','https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/LICENSE'),('raw_ddl','https://raw.githubusercontent.com/kiruha355/rwb_hak/2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e/scripts/init/02_raw_ddl.sql'),('numeric_pg16','https://www.postgresql.org/docs/16/datatype-numeric.html'),('aggregate_pg16','https://www.postgresql.org/docs/16/functions-aggregate.html'),('censoring_nist','https://itl.nist.gov/div898/handbook/apr/section1/apr131.htm'),('kimball_additivity','https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/'),('example_fanout','https://raw.githubusercontent.com/hudasf/Olist-Dashboard-Streamlit/b9fd7a8bd79515e284980fbefe226c0b2dbf5838/olist_dataAnalyst.py'),('example_category_sql','https://raw.githubusercontent.com/tolamoye/Olist-E-commerce-Data-Analysis/c609dfa753e84ebeca0711344a650668f4e81652/Olist%20data.sql'),('example_distinct','https://raw.githubusercontent.com/miguelvotre/olist-ecommerce-analytics/ac2b1b4e5abf84d086809fd2a9751f3c39fef4f0/dashboard/pages/1_overview.py'),('example_review','https://raw.githubusercontent.com/miguelvotre/olist-ecommerce-analytics/ac2b1b4e5abf84d086809fd2a9751f3c39fef4f0/dashboard/pages/3_categories.py'),('secondary_dictionary','https://raw.githubusercontent.com/aduverger/olist/master/data/README.md')]
with (O/'source-checks.jsonl').open('w') as out:
 for name,url in sources:
  entry={'name':name,'url':url,'accessed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'urllib GET, static read; no fetched code executed'}
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'rwb-independent-review/1.0','Accept':'application/vnd.github+json' if 'api.github.com' in url else '*/*'})
   with urllib.request.urlopen(req,timeout=20) as response: b=response.read(2000000); entry.update(http_status=response.status,bytes_read=len(b),sha256=hashlib.sha256(b).hexdigest(),result='opened')
   if name=='olist_tree':
    a=json.loads(b); tree={x['name']:x['sha'] for x in a}; entry['result']={'tree_entries':len(a),'csv_count':sum(x['name'].endswith('.csv') for x in a),'eight_local_blob_match':all(tree.get(n)==v['git_blob_sha1'] for n,v in csvdata['files'].items()),'geolocation_in_tree':'olist_geolocation_dataset.csv' in tree}
   elif name=='kaggle_metadata':
    a=json.loads(b); entry['result']={'licenseName':a.get('licenseName'),'currentVersionNumber':a.get('currentVersionNumber'),'datasetTitle':a.get('title')}
   elif name=='organizer_repo':
    a=json.loads(b);entry['result']={'default_branch':a.get('default_branch'),'owner':a.get('owner',{}).get('login'),'authority':'not established'}
   elif name=='organizer_head':entry['result']={'sha':json.loads(b).get('sha')}
   elif name.startswith('organizer_'):
    rel=name[len('organizer_'):]; local=O.parents[3]/'hack-context/hackathon-students'/rel; entry['result']={'sha256_matches_local':hashlib.sha256(local.read_bytes()).hexdigest()==entry['sha256']}
  except Exception as e:entry.update(result='failed',error=f'{type(e).__name__}: {e}')
  out.write(json.dumps(entry,ensure_ascii=False)+'\n'); out.flush()
