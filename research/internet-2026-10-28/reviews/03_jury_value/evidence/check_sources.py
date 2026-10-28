import concurrent.futures, datetime, hashlib, json, pathlib, urllib.request, urllib.error
root=pathlib.Path(__file__).resolve().parents[5]
out=pathlib.Path(__file__).resolve().parents[1]/'source-checks.jsonl'
base='https://raw.githubusercontent.com/'
rows=[
(base+'daniilivanovp-droid/hackathon-students/3da32d149bfa14dca3fdb0c5863d0771c38efbfc/'+p,'candidate organizer '+p,'hack-context/hackathon-students/'+p) for p in ('README.md','docs/handout.md','docs/tasks.md')]+[
(base+'hudasf/Olist-Dashboard-Streamlit/b9fd7a8bd79515e284980fbefe226c0b2dbf5838/olist_dataAnalyst.py','L29-33,109-129',None),
(base+'miguelvotre/olist-ecommerce-analytics/ac2b1b4e5abf84d086809fd2a9751f3c39fef4f0/dashboard/pages/1_overview.py','L43-55',None),
(base+'miguelvotre/olist-ecommerce-analytics/ac2b1b4e5abf84d086809fd2a9751f3c39fef4f0/dashboard/pages/3_categories.py','L22-23,65-71',None),
(base+'miguelvotre/olist-ecommerce-analytics/ac2b1b4e5abf84d086809fd2a9751f3c39fef4f0/dashboard/utils/db_client.py','L49-52,114-124',None),
(base+'yzinchenko-data/olist-ecommerce-analytics/443ebe2bb86f02c987d4e1e4c24a4824db908e79/sql/03_create_order_mart.sql','L29-64',None),
(base+'olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/README.md','L1-12 separate Olist exercise',None),
(base+'aduverger/olist/master/data/README.md','L84-91 secondary mutable dictionary',None),
('https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/','ratio components',None),
('https://itl.nist.gov/div898/handbook/apr/section1/apr131.htm','8.1.3.1 censoring',None),
('https://www.postgresql.org/docs/16/ddl-partitioning.html','5.11.2.3 uniqueness and 5.11.4 pruning',None),
('https://www.postgresql.org/docs/16/using-explain.html','14.1.3 caveats',None),
('https://www.postgresql.org/docs/16/brin-intro.html','71.1 correlation and recheck',None),
('https://www.postgresql.org/docs/16/sql-refreshmaterializedview.html','CONCURRENTLY restrictions',None),
('https://docs.getdbt.com/best-practices/how-we-handle-cdc/2-choosing-incremental-or-snapshots','Snapshot only',None),
('https://docs.getdbt.com/docs/build/incremental-models','incremental filters and schema changes',None),
('https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce','data card content',None),
]
def run(row):
 url,loc,local=row; time=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'); rec={'url':url,'accessed_at':time,'locator':loc,'method':'HTTP GET, no browser'}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'RWB-research-source-check/1.0'})
  with urllib.request.urlopen(req,timeout=15) as resp: data=resp.read(); rec.update(http_status=resp.status,final_url=resp.url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),result='opened; static source only')
  if local: rec['equals_local_copy']=(data==(root/local).read_bytes())
 except Exception as e: rec.update(result='fetch error',error=str(e))
 return rec
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: results=list(pool.map(run,rows))
out.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in results))
for x in results: print(x['http_status'] if 'http_status' in x else x['error'],x['url'],x.get('equals_local_copy',''))
