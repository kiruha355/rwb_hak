#!/usr/bin/env python3
"""Tiny PG16 driver/transaction check, no Olist data and no model build.

Creates only its own temporary 16MB server, tests SELECT transport and read-only
enforcement, then stops/removes that server. Never touches an existing endpoint.
"""
from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import psycopg
from psycopg.rows import dict_row

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('verify',ROOT/'scripts/verify-full-olist.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
output=Path(sys.argv[1]).resolve();output.mkdir(parents=True,exist_ok=False)
pg=Path('/opt/homebrew/opt/postgresql@16/bin')
report={'scope':'three synthetic SELECT rows only; driver/READ ONLY test, no full Olist, no model lifecycle',
        'at_utc':datetime.now(timezone.utc).isoformat(),'status':'in_progress','runner_sha256':m.file_sha(ROOT/'scripts/verify-full-olist.py')}
started=False
with tempfile.TemporaryDirectory(prefix='olist-ro-driver-') as runtime:
    runtime=Path(runtime);socket=runtime/'socket';socket.mkdir();data=runtime/'data'
    env={k:v for k,v in os.environ.items() if not k.startswith('PG')}
    def run(name,argv):
        r=subprocess.run([str(x) for x in argv],env=env,text=True,capture_output=True,timeout=20)
        (output/(name+'.log')).write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(name+' failed')
        return r.stdout
    try:
        report['server']=run('version',[pg/'postgres','--version']).strip()
        if ' 16.' not in report['server']:raise RuntimeError('PG16 required')
        run('init',[pg/'initdb','-D',data,'-U','olist_ro_driver','-A','trust','--no-locale','--encoding=UTF8'])
        run('start',[pg/'pg_ctl','-D',data,'-l',runtime/'server.log','-w','-o',
            f"-F -h '' -k {socket} -p 55486 -c shared_buffers=16MB -c max_connections=5 -c work_mem=1MB -c max_parallel_workers=0",'start'])
        started=True
        with psycopg.connect(host=str(socket),port=55486,dbname='postgres',user='olist_ro_driver',
            options='-c default_transaction_read_only=on -c statement_timeout=3000',autocommit=True,row_factory=dict_row) as conn:
            conn.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
            row=conn.execute("SELECT current_setting('transaction_isolation') AS isolation,current_setting('transaction_read_only') AS read_only").fetchone()
            assert row=={'isolation':'repeatable read','read_only':'on'}
            report['transaction']=row
            with conn.cursor(name='driver_values') as c:
                c.execute("SELECT * FROM (VALUES (1,1.20::numeric,NULL::text), (2,0::numeric,''::text),(1,1.20::numeric,NULL::text)) v(id,amount,note)")
                actual=m.multiset(c)
            expected=m.multiset([dict(id=1,amount=Decimal('1.2'),note=None),dict(id=2,amount=Decimal('0'),note=''),dict(id=1,amount=Decimal('1.20'),note=None)])
            assert actual==expected
            report['named_cursor_hash_comparison']={'status':'pass',**actual}
            conn.execute('SAVEPOINT reject_write')
            try:
                conn.execute('CREATE TABLE public.should_never_exist(id integer)')
                raise RuntimeError('READ ONLY did not reject DDL')
            except psycopg.errors.ReadOnlySqlTransaction as e:
                report['write_rejected_sqlstate']=e.sqlstate
                conn.execute('ROLLBACK TO SAVEPOINT reject_write')
            conn.execute('ROLLBACK')
            assert conn.execute("SELECT to_regclass('public.should_never_exist') AS name").fetchone()['name'] is None
        report['status']='pass'
    finally:
        if started:run('stop_own_server',[pg/'pg_ctl','-D',data,'-m','fast','-w','stop'])
        report['runtime_removed_on_exit']=True
        (output/'summary.json').write_bytes(m.encoded(report)+b'\n')
print(json.dumps({'status':report['status'],'scope':report['scope'],'evidence':str(output)},ensure_ascii=False))
