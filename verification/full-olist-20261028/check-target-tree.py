#!/usr/bin/env python3
"""Check pinned dependencies and expected core columns without changing index."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('full_olist',ROOT/'scripts/verify-full-olist.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=Path(sys.argv[1]);ref=m.INPUT
get=lambda p:m.blob(ROOT,ref,p).decode()
oracle=m.Oracle(Path(sys.argv[2]));oracle.answers()
columns={}
sql=get('model/10_dims.sql')+'\n'+get('model/20_facts.sql')
for table,rows in oracle.core_expected():
    first=next(iter(rows))
    definition=re.search(r'CREATE TABLE core\.'+table+r' \((.*?)\n\);',sql,re.S).group(1)
    actual=set(re.findall(r'^    (\w+) (?:text|integer|numeric|timestamp|date|boolean)\b',definition,re.M))
    assert actual==set(first),(table,sorted(actual),sorted(first))
    columns[table]=sorted(actual)
required=['tests/model/input-manifest.lock.json','model/55_answers_block_b.sql',
          'docs/phase-20261028/experiments/payments-prices/results.json',
          'docs/phase-20261028/experiments/delivery-data/results.json',
          'docs/phase-20261028/experiments/review-data/results.json']
code={}
for p in required:code[p]=m.sha(m.blob(ROOT,ref,p))
views=set(re.findall(r'CREATE VIEW (mart\.\w+) AS',get('model/50_answers.sql')+get('model/55_answers_block_b.sql')))
for path in ['answers/'+q+'.sql' for q in ('q01','q02','q03','q04','q04_window','q05')]+['answers/q06-q10/'+q+'.sql' for q in ('q06','q07','q08','q09','q10','q10_coverage')]:
    queries=m.statements(get(path))
    assert all(v in views for v in re.findall(r'FROM (mart\.q\w+)',get(path))),path
    code[path]=m.sha(get(path).encode())
main=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','origin/main'],text=True).strip()
integration=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','origin/t3/integrate-q6-q10-marts'],text=True).strip()
missing=[]
for p in required:
    r=subprocess.run(['git','-C',str(ROOT),'cat-file','-e',main+':'+p],capture_output=True)
    if r.returncode:missing.append(p)
report=dict(status='pass_pinned_integration_dependencies',input_commit=ref,fetched_main=main,fetched_integration=integration,
    main_missing_pinned_runtime_paths=missing,core_projection_columns=columns,pinned_dependency_sha256=code,
    limit='Static target-tree check; no DB build, no history-integration claim')
out.write_bytes(m.encoded(report)+b'\n')
print(json.dumps({'status':report['status'],'core_tables':len(columns),'main_missing_dependencies':missing},ensure_ascii=False))
