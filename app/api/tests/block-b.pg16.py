#!/usr/bin/env python3
"""Small stage-55/API shape check; no installs, CSV loading or shared runtime.

Usage: python3 app/api/tests/block-b.pg16.py
Creates and stops only its own PG16 server, 16MB buffers, Unix socket, no TCP.
The Node adapter calls the real block-b.js with prepared queries over psql JSON;
this is not Express/pg HTTP or the full Olist lifecycle.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
PGBIN = Path('/opt/homebrew/opt/postgresql@16/bin')
FILES = ['app/api/block-b.js', 'app/api/server.js',
         'app/api/tests/block-b.pg16.mjs', 'app/api/tests/block-b.pg16.py',
         'scripts/init/02_raw_ddl.sql', 'tests/model/fixtures/base.sql',
         'model/10_dims.sql', 'model/20_facts.sql', 'model/40_mart.sql',
         'model/55_answers_block_b.sql']


def main():
    version = subprocess.check_output([PGBIN / 'postgres', '--version'], text=True).strip()
    if ' 16.' not in version:
        raise SystemExit('Requires the existing PostgreSQL 16 installation')
    summary = {'at_utc': datetime.now(timezone.utc).isoformat(), 'postgres': version,
               'files_sha256': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}}
    started = False
    with tempfile.TemporaryDirectory(prefix='block-b-pg16-') as temp:
        runtime = Path(temp)
        socket = runtime / 'socket'
        socket.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith('PG') and k != 'DATABASE_URL'}
        env.update(PGHOST=str(socket), PGPORT='55486', PGDATABASE='block_b_fixture',
                   PGUSER='block_b_fixture', PGCONNECT_TIMEOUT='5', PGOPTIONS='',
                   RWB_BLOCK_B_FIXTURE='1', RWB_BLOCK_B_PSQL=str(PGBIN / 'psql'))

        def run(argv, stdin=None):
            result = subprocess.run([str(a) for a in argv], input=stdin, cwd=ROOT,
                                    env=env, text=True, capture_output=True, timeout=40)
            if result.returncode:
                raise RuntimeError(f'{Path(argv[0]).name}: exit {result.returncode}\n{result.stdout}{result.stderr}')
            return result.stdout

        try:
            run([PGBIN / 'initdb', '-D', runtime / 'data', '-U', 'block_b_fixture',
                 '-A', 'trust', '--no-locale', '--encoding=UTF8'])
            run([PGBIN / 'pg_ctl', '-D', runtime / 'data', '-l', runtime / 'server.log', '-w',
                 '-o', f"-F -h '' -k {socket} -p 55486 -c shared_buffers=16MB -c max_connections=5 -c work_mem=1MB -c max_parallel_workers=0",
                 'start'])
            started = True
            run([PGBIN / 'createdb', 'block_b_fixture'])
            sql = 'CREATE SCHEMA raw; CREATE SCHEMA core; CREATE SCHEMA mart;\n'
            for path in ('scripts/init/02_raw_ddl.sql', 'tests/model/fixtures/base.sql'):
                sql += (ROOT / path).read_text() + '\n'
            sql += """
                UPDATE raw.orders SET order_status='canceled' WHERE order_id='neither';
                UPDATE raw.orders SET order_purchase_timestamp='2018-01-01 10:00:00'
                  WHERE order_id IN ('fanout','all-null');
                UPDATE raw.orders SET order_purchase_timestamp=NULL WHERE order_id='partial';
                INSERT INTO raw.order_items(order_id,order_item_id,product_id,seller_id,price)
                  VALUES ('partial','3','p1','s1',NULL);
                UPDATE raw.customers SET customer_state=NULL
                  WHERE customer_id IN ('c-fanout','c-all-null');
            """
            for path in ('model/10_dims.sql', 'model/20_facts.sql', 'model/40_mart.sql',
                         'model/55_answers_block_b.sql'):
                sql += (ROOT / path).read_text() + '\n'
            run([PGBIN / 'psql', '-X', '-w', '-q', '-v', 'ON_ERROR_STOP=1', '-1'], sql)
            summary['result'] = json.loads(run(['node', 'app/api/tests/block-b.pg16.mjs']))
        finally:
            if started:
                run([PGBIN / 'pg_ctl', '-D', runtime / 'data', '-m', 'fast', '-w', 'stop'])
                summary['own_server_stopped'] = True
    summary['runtime_removed'] = True
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
