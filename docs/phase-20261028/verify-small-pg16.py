#!/usr/bin/env python3
"""Run only small synthetic fixtures on a private, temporary PG16 server.

No downloads, existing endpoints or Olist CSV loading. Retain evidence, remove
only the server created by this process. Usage: script.py CHECKOUT EVIDENCE_DIR.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
evidence = Path(sys.argv[2]).resolve()
evidence.mkdir(parents=True, exist_ok=False)
pgbin = Path('/opt/homebrew/opt/postgresql@16/bin')
version = subprocess.check_output([pgbin / 'postgres', '--version'], text=True).strip()
if ' 16.' not in version:
    raise SystemExit('Requires the existing PostgreSQL 16 installation')
manifest = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for directory in ('model', 'answers/q06-q10')
            for p in sorted((root / directory).rglob('*'))
            if p.is_file() and p.suffix in ('.sql', '.py')}
for name in ('scripts/build-model.sh', 'scripts/init/02_raw_ddl.sql',
             'tests/model/fixtures/base.sql', 'tests/model/fingerprint.sql',
             'tests/model/rollback.sql'):
    manifest[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
summary = {'scope': 'synthetic_fixture_only', 'q6_q10_behavior_orders': 16, 'lifecycle_orders': 10, 'server': version,
           'at_utc': datetime.now(timezone.utc).isoformat(), 'files_sha256': manifest,
           'full_olist': 'not_run', 'csv_raw_equality': 'not_run', 'checks': {}}
started = False
with tempfile.TemporaryDirectory(prefix='capibara-pg16-small-') as runtime:
    runtime = Path(runtime)
    data = runtime / 'data'
    socket = runtime / 'socket'
    socket.mkdir()
    env = dict(os.environ)
    for key in ('PGSERVICE', 'PGSERVICEFILE', 'DATABASE_URL'):
        env.pop(key, None)
    env.update(PGHOST=str(socket), PGPORT='55482', PGDATABASE='q6_q10_fixture',
               PGUSER='capibara_fixture', PGOPTIONS='', PGCONNECT_TIMEOUT='5',
               RWB_RAW_RELOAD_PAUSED='1', RWB_DB_MODE='host',
               PATH=str(pgbin) + os.pathsep + env['PATH'])

    def run(name, argv, expected=0, stdin=None):
        result = subprocess.run([str(a) for a in argv], cwd=root, env=env, input=stdin,
                                text=True, capture_output=True, timeout=40)
        (evidence / (name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode != expected:
            raise RuntimeError(f'{name}: exit {result.returncode}, expected {expected}; see evidence')
        summary['checks'][name] = {'exit_code': result.returncode, 'status': 'pass'}
        return result.stdout

    psql = [pgbin / 'psql', '-X', '-w', '-v', 'ON_ERROR_STOP=1', '-P', 'pager=off']
    try:
        run('initdb', [pgbin / 'initdb', '-D', data, '-U', 'capibara_fixture', '-A', 'trust', '--no-locale', '--encoding=UTF8'])
        run('start', [pgbin / 'pg_ctl', '-D', data, '-l', runtime / 'server.log', '-w',
                      '-o', f"-F -h '' -k {socket} -p 55482 -c shared_buffers=16MB -c max_connections=5 -c work_mem=1MB -c max_parallel_workers=0", 'start'])
        started = True
        run('create_fixture_db', [pgbin / 'createdb', 'q6_q10_fixture'])
        run('q6_q10_behavior', [sys.executable, 'answers/q06-q10/test_fixture.py'])
        raw = 'CREATE SCHEMA raw;\n' + (root / 'scripts/init/02_raw_ddl.sql').read_text()
        raw += '\n' + (root / 'tests/model/fixtures/base.sql').read_text()
        run('load_ten_order_fixture', psql + ['-1'], stdin=raw)
        fingerprints = psql + ['-qAt', '-F', '\t', '-f', 'tests/model/fingerprint.sql']
        before = run('raw_before', fingerprints)
        run('clean_build', ['bash', 'scripts/build-model.sh', 'build'])
        first = run('first', fingerprints)
        run('rebuild', ['bash', 'scripts/build-model.sh', 'build'])
        second = run('second', fingerprints)
        if first != second:
            raise RuntimeError('Rebuild changed content or object definitions')
        rollback = run('late_failure', psql + ['-1', '-f', 'tests/model/rollback.sql'], expected=3)
        failure_log = (evidence / 'late_failure.log').read_text()
        if 'W11_INJECTED_LATE_FAILURE_AFTER_ALL_CHECKS' not in failure_log:
            raise RuntimeError('The intended late failure was not reached')
        after = run('after_rollback', fingerprints)
        if second != after:
            raise RuntimeError('Rollback changed the committed model')
        raw_lines = lambda s: [line for line in s.splitlines() if line.startswith('raw.')]
        if not raw_lines(before) or raw_lines(before) != raw_lines(after):
            raise RuntimeError('Raw changed or its fingerprints are missing')
        run('answers_entrypoint', ['bash', 'scripts/build-model.sh', 'answers'])
        run('invariants', ['bash', 'scripts/build-model.sh', 'check'])
        summary['status'] = 'pass'
    except Exception as exc:
        summary.update(status='fail', error=str(exc))
        raise
    finally:
        if started:
            run('stop_own_server', [pgbin / 'pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'])
        summary['runtime_removed_on_exit'] = True
        (evidence / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': summary['status'], 'server': version, 'evidence': str(evidence),
                  'scope': summary['scope']}, ensure_ascii=False))
