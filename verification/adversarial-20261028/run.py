#!/usr/bin/env python3
"""Run pinned actual wrappers on tiny PG16 fixtures, using stdlib + existing PG.

Usage: python3 verification/adversarial-20261028/run.py --output results
Never connects to an existing server, installs packages, or loads full Olist.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from fixture import fixture, insert_sql, metamorphic
from oracle import expected, compare, QUERIES, KEYS

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
INPUT = 'aab62d7a59f196be051df12466fb21c0da4659b9'
REQUIREMENTS = '558f0f6a38110acc9fcf4386a7e53ece973aedf5'
PGBIN = Path('/opt/homebrew/opt/postgresql@16/bin')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


MUTATIONS = [
    ('drop_childless_orders', 'model/40_mart.sql', 'LEFT JOIN payments p ON p.order_id = o.order_id', 'JOIN payments p ON p.order_id = o.order_id'),
    ('missing_money_becomes_zero', 'model/40_mart.sql', 'i.item_revenue, i.freight_amount, i.order_gmv,', 'coalesce(i.item_revenue, 0) AS item_revenue, i.freight_amount, i.order_gmv,'),
    ('q6_count_rows_not_distinct', 'model/55_answers_block_b.sql', 'count(DISTINCT price) AS distinct_prices', 'count(price) AS distinct_prices'),
    ('q7_all_orders_denominator', 'model/55_answers_block_b.sql', '/ nullif(count(is_late), 0)', '/ nullif(count(*), 0)'),
    ('q7_threshold_exclusive', 'answers/q06-q10/q07.sql', 'orders_count >= 500::bigint', 'orders_count > 500::bigint'),
    ('q8_wrong_childless_predicate', 'model/55_answers_block_b.sql', 'source_rows_count = 0', 'source_rows_count = 1'),
    ('q9_includes_next_year', 'model/55_answers_block_b.sql', "< timestamp '2019-01-01'", "<= timestamp '2019-01-01'"),
    ('q10_repeat_score_fanout', 'model/55_answers_block_b.sql', 'SELECT DISTINCT order_id, review_score FROM core.fact_review', 'SELECT order_id, review_score FROM core.fact_review'),
    ('q10_all_orders_denominator', 'model/55_answers_block_b.sql', '/ nullif(count(a.is_late), 0)', '/ nullif(count(a.order_id), 0)'),
    ('negative_delivery_duration', 'model/40_mart.sql', 'is_delivered AND order_delivered_customer_date >= order_purchase_timestamp', 'is_delivered AND order_delivered_customer_date IS NOT NULL AND order_purchase_timestamp IS NOT NULL'),
    ('choose_conflicting_review_payload', 'model/40_mart.sql', 'p.review_id = v.review_id AND v.payload_variant_count = 1', 'p.review_id = v.review_id'),
]

NEGATIVES = [
    ('duplicate_item_key', 'INSERT INTO raw.order_items SELECT * FROM raw.order_items LIMIT 1', '23505'),
    ('orphan_product', "UPDATE raw.order_items SET product_id='no-such-product' WHERE order_id='zero'", '23503'),
    ('nonfinite_price', "UPDATE raw.order_items SET price='NaN' WHERE order_id='zero'", 'Input type/key precheck failed'),
    ('blank_order_identity', "UPDATE raw.orders SET order_id='   ' WHERE order_id='no-child'", 'Input type/key precheck failed'),
    ('malformed_timestamp', "UPDATE raw.orders SET order_purchase_timestamp='not-a-date' WHERE order_id='zero'", 'Input type/key precheck failed'),
    ('fractional_timestamp_policy', "UPDATE raw.orders SET order_purchase_timestamp='2018-01-01 00:00:00.123456' WHERE order_id='zero'", 'Input type/key precheck failed'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='results')
    args = parser.parse_args()
    out = (HERE / args.output).resolve()
    if not out.is_relative_to(HERE):
        raise SystemExit('Output must be inside OWNED directory')
    out.mkdir(exist_ok=False)
    (out / 'logs').mkdir()
    summary = dict(input_sha=INPUT, requirements_sha=REQUIREMENTS,
                   utc_start=datetime.now(timezone.utc).isoformat(), scope='tiny_synthetic_actual_wrappers',
                   full_olist_lifecycle='NOT_RUN', csv_raw_equality='NOT_RUN', history_runtime='OUT_OF_SCOPE',
                   baseline={}, metamorphic={}, mutations={}, negatives={}, status='running')
    commands = []
    temp_code = tempfile.TemporaryDirectory(prefix='.runtime-code-', dir=HERE)
    # Short socket path is required by PostgreSQL Unix-domain path length limits.
    temp_server = tempfile.TemporaryDirectory(prefix='rwb-adversarial-pg16-')
    code, runtime = Path(temp_code.name), Path(temp_server.name)
    data, sock = runtime / 'data', runtime / 's'
    sock.mkdir()
    started = False
    env = {k: v for k, v in os.environ.items() if not k.startswith('PG') and k not in ('DATABASE_URL',)}
    env.update(PGHOST=str(sock), PGPORT='55483', PGUSER='adversarial_fixture', PGDATABASE='adversarial_fixture',
               PGCONNECT_TIMEOUT='3', RWB_RAW_RELOAD_PAUSED='1', RWB_DB_MODE='host',
               TMPDIR=str(runtime), PATH=str(PGBIN) + os.pathsep + env.get('PATH', ''), PYTHONDONTWRITEBYTECODE='1')
    psql = [str(PGBIN / 'psql'), '-X', '-w', '-v', 'ON_ERROR_STOP=1', '-qAt', '-P', 'pager=off']
    def run(label, argv, stdin=None, required=True):
        t0 = time.monotonic()
        proc = subprocess.run([str(x) for x in argv], input=stdin, text=True, capture_output=True,
                              cwd=code, env=env, timeout=50)
        (out / 'logs' / (label + '.log')).write_text(proc.stdout + proc.stderr)
        commands.append(dict(label=label, argv=[str(x).replace(str(code), '<private-code>').replace(str(runtime), '<private-server>') for x in argv],
                             stdin_sha256=sha(stdin.encode()) if stdin is not None else None,
                             exit_code=proc.returncode, seconds=round(time.monotonic()-t0, 3)))
        if required and proc.returncode:
            raise RuntimeError(f'{label}: exit {proc.returncode}; see logs/{label}.log')
        return proc
    def query(label, sql):
        p = run(label, psql, 'SELECT coalesce(json_agg(x),\'[]\'::json) FROM (' + sql.strip().rstrip(';') + ') x;')
        return json.loads(p.stdout, parse_float=Decimal)
    def fingerprint(label, schemas):
        # Snapshot actual rows and definitions, independent of production fingerprint wrapper.
        relations = query(label + '_catalog', "SELECT n.nspname AS schema,c.relname AS name,c.relkind AS kind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN (" + ','.join("'" + s + "'" for s in schemas) + ") AND c.relkind IN ('r','v') ORDER BY 1,2")
        values = {}
        for r in relations:
            relation = r['schema'] + '.' + r['name']
            columns = "to_jsonb(t) - 'checked_at'" if relation == 'core.check_results' else 'to_jsonb(t)'
            rows = query(label + '_' + relation, 'SELECT ' + columns + ' AS row FROM ' + relation + ' t')
            values[relation] = sorted(json.dumps(x, sort_keys=True, default=str) for x in rows)
        schema_sql = ','.join("'" + s + "'" for s in schemas)
        values['definitions'] = query(label + '_defs', "SELECT n.nspname,c.relname,pg_get_viewdef(c.oid) AS definition FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN (" + schema_sql + ") AND c.relkind='v' ORDER BY 1,2")
        values['constraints'] = query(label + '_constraints', "SELECT conrelid::regclass::text AS relation,conname,pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE connamespace IN (SELECT oid FROM pg_namespace WHERE nspname IN (" + schema_sql + ")) ORDER BY 1,2")
        return sha(json.dumps(values, sort_keys=True, default=str).encode())
    def load(label, tables):
        ddl = (code / 'scripts/init/02_raw_ddl.sql').read_text()
        run(label + '_raw_load', psql, 'CREATE SCHEMA IF NOT EXISTS raw;\n' + ddl + insert_sql(tables))
    def build(label, required=True):
        return run(label, ['bash', 'scripts/build-model.sh', 'build'], required=required)
    def behavior(label, tables):
        wanted = expected(tables)
        actual, checks = {}, {}
        for key, sql in QUERIES.items():
            actual[key] = query(label + '_' + key, sql)
            checks[key] = compare(key, actual[key], wanted[key], KEYS[key])
        q7 = (code / 'answers/q06-q10/q07.sql').read_text()
        # Execute actual answer selector; views intentionally have no threshold.
        actual['q7_original_selector'] = query(label + '_q7_original_selector', q7)
        compare('q7_original_selector', actual['q7_original_selector'], [], KEYS['q7'])
        if q7.count('500::bigint') != 1:
            raise RuntimeError('Unexpected threshold selector: substitution must be exact')
        actual['q7_scaled_selector'] = query(label + '_q7_scaled_selector', q7.replace('500::bigint', '2::bigint'))
        wanted_scaled = [r for r in wanted['q7'] if r['orders_count'] >= 2]
        checks['q7_scaled_selector'] = compare('q7_scaled_selector', actual['q7_scaled_selector'], wanted_scaled, KEYS['q7'])
        status = query(label + '_new_status', "SELECT order_status,is_revenue FROM core.dim_order_status WHERE order_status='returned_custom'")
        assert status == [dict(order_status='returned_custom', is_revenue=False)]
        deadlines = query(label + '_deadline_variants', "SELECT is_handover_after_min_item_deadline AS min_late,is_handover_after_max_item_deadline AS max_late FROM mart.v_order_delivery_variants WHERE order_id='fanout'")
        assert deadlines == [dict(min_late=True, max_late=False)]
        independent = query(label + '_independent_intervals', "SELECT purchase_to_delivery_days,purchase_to_carrier_days,carrier_to_delivery_days FROM mart.v_order_delivery_variants WHERE order_id='carrier-negative'")
        assert independent == [dict(purchase_to_delivery_days=1, purchase_to_carrier_days=None, carrier_to_delivery_days=2)]
        dump(out / (label + '_actual.json'), actual)
        return dict(status='pass', comparisons=sum(checks.values()), relation_checks=checks), actual
    try:
        version = subprocess.check_output([str(PGBIN / 'postgres'), '--version'], text=True).strip()
        if not version.startswith('postgres (PostgreSQL) 16.'):
            raise RuntimeError('Existing PG16 is required; no installation fallback')
        summary['server'] = dict(version=version, shared_buffers='16MB', max_connections=5,
                                 work_mem='1MB', max_parallel_workers=0, tcp_listen=False)
        names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', INPUT,
                                         'model', 'answers', 'scripts/build-model.sh', 'scripts/init/02_raw_ddl.sql'],
                                        cwd=REPO, text=True).splitlines()
        source_manifest = {}
        for name in names:
            if not name.endswith(('.sql', '.sh')):
                continue
            content = subprocess.check_output(['git', 'show', INPUT + ':' + name], cwd=REPO)
            path = code / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            source_manifest[name] = dict(sha256=sha(content), git_blob=subprocess.check_output(
                ['git', 'rev-parse', INPUT + ':' + name], cwd=REPO, text=True).strip())
        dump(out / 'source_manifest.json', source_manifest)
        tasks = subprocess.check_output(['git', 'show', REQUIREMENTS + ':docs/tasks.md'], cwd=REPO)
        (out / 'requirements.source.md').write_bytes(tasks)
        summary['requirements_blob_sha256'] = sha(tasks)
        summary['runner_sha256'] = {p.name: sha(p.read_bytes()) for p in (HERE / 'run.py', HERE / 'fixture.py', HERE / 'oracle.py')}
        (out / 'runner-source').mkdir()
        for p in (HERE / 'run.py', HERE / 'fixture.py', HERE / 'oracle.py'):
            shutil.copyfile(p, out / 'runner-source' / p.name)
        base = fixture()
        dump(out / 'fixture.json', base)
        (out / 'fixture.sql').write_text(insert_sql(base))
        summary['fixture_rows'] = {name: len(rows) for name, rows in base.items()}
        run('initdb', [PGBIN / 'initdb', '-D', data, '-U', 'adversarial_fixture', '-A', 'trust', '--no-locale', '--encoding=UTF8'])
        run('start_own_server', [PGBIN / 'pg_ctl', '-D', data, '-l', runtime / 'server.log', '-w', '-o',
            f"-F -h '' -k {sock} -p 55483 -c shared_buffers=16MB -c max_connections=5 -c work_mem=1MB -c max_parallel_workers=0", 'start'])
        started = True
        run('createdb', [PGBIN / 'createdb', 'adversarial_fixture'])
        load('baseline', base)
        raw_before = fingerprint('baseline_raw_before', ['raw'])
        build('baseline_build')
        summary['baseline'], baseline_actual = behavior('baseline', base)
        first = fingerprint('first', ['raw', 'core', 'mart'])
        build('baseline_rebuild')
        second = fingerprint('second', ['raw', 'core', 'mart'])
        assert first == second, 'Rebuild changed rows or DDL'
        raw_after = fingerprint('baseline_raw_after', ['raw'])
        assert raw_before == raw_after, 'Build/rebuild changed raw content or DDL'
        summary['lifecycle'] = dict(rebuild_equal=True, first_fingerprint=first, second_fingerprint=second,
                                    raw_unchanged=True, raw_before_fingerprint=raw_before, raw_after_fingerprint=raw_after)
        raw_equal = query('raw_unchanged', 'SELECT count(*) AS n FROM raw.orders') == [dict(n=len(base['orders']))]
        assert raw_equal
        run('answers_actual_wrapper', ['bash', 'scripts/build-model.sh', 'answers'])
        run('check_actual_wrapper', ['bash', 'scripts/build-model.sh', 'check'])
        late_path = code / 'model/build.sql'
        late_original = late_path.read_text()
        late_before = fingerprint('late_before', ['raw', 'core', 'mart'])
        late_path.write_text(late_original + "\nDO $$ BEGIN RAISE EXCEPTION 'ADVERSARIAL_LATE_FAILURE_AFTER_ALL_CHECKS'; END $$;\n")
        try:
            late_failure = build('late_failure_actual_wrapper', required=False)
            assert late_failure.returncode == 3 and 'ADVERSARIAL_LATE_FAILURE_AFTER_ALL_CHECKS' in late_failure.stderr
        finally:
            late_path.write_text(late_original)
        late_after = fingerprint('late_after', ['raw', 'core', 'mart'])
        assert late_before == late_after, 'Late failure changed committed model/raw'
        summary['lifecycle']['late_error_rollback'] = dict(before=late_before, after=late_after,
            marker='ADVERSARIAL_LATE_FAILURE_AFTER_ALL_CHECKS', evidence='logs/late_failure_actual_wrapper.log')
        # Exact SQL equality of raw rows to typed fixture inputs, excluding loader metadata.
        raw_content = {}
        for table, rows in base.items():
            columns = sorted(set().union(*(r.keys() for r in rows)))
            observed = query('raw_retained_' + table, 'SELECT ' + ','.join(columns) + ' FROM raw.' + table)
            expected_rows = [{c: r.get(c) for c in columns} for r in rows]
            canon = lambda rs: sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rs)
            assert canon(observed) == canon(expected_rows), table
            raw_content[table] = sha(json.dumps(canon(observed)).encode())
        summary['lifecycle']['raw_fixture_equality'] = raw_content
        for variant in ('more_children', 'item_replication', 'nonrevenue_price_leader', 'permuted_input', 'complete_money'):
            changed = metamorphic(base, variant)
            load(variant, changed); build(variant + '_build')
            summary['metamorphic'][variant], actual = behavior(variant, changed)
            if variant in ('more_children', 'permuted_input'):
                invariant = ('q1', 'q2', 'q4', 'q5', 'q6', 'q7', 'q8', 'q10', 'q10_coverage')
                for key in invariant:
                    compare('metamorphic_' + key, actual[key], baseline_actual[key], KEYS[key])
                summary['metamorphic'][variant]['unchanged_relations'] = list(invariant)
        for name, path, before, after in MUTATIONS:
            load('mut_' + name, base)
            file = code / path
            original = file.read_text()
            if before not in original:
                raise RuntimeError('Mutation anchor absent: ' + name)
            changed = original.replace(before, after)
            file.write_text(changed)
            mutation = dict(path=path, before=before, after=after, replacements=original.count(before),
                            before_sha256=sha(original.encode()), after_sha256=sha(changed.encode()))
            try:
                built = build('mut_' + name + '_build', required=False)
                if built.returncode:
                    if 'core invariant checks failed' not in built.stderr:
                        raise RuntimeError('Mutation failed outside intended invariant checks: ' + name)
                    mutation.update(status='killed', detected_by='actual_build_invariants', evidence='logs/mut_' + name + '_build.log')
                else:
                    try:
                        behavior('mut_' + name, base)
                    except AssertionError as exc:
                        mutation.update(status='killed', detected_by='independent_behavior_oracle', counterexample=str(exc))
                    else:
                        mutation.update(status='survived')
                summary['mutations'][name] = mutation
            finally:
                file.write_text(original)
        assert all(m['status'] == 'killed' for m in summary['mutations'].values()), 'A mutation survived'
        load('negative_base', base); build('negative_base_build')
        for name, sql, diagnostic in NEGATIVES:
            # Reset raw input; keep committed model to verify failed rebuild rollback.
            load('negative_reset_' + name, base)
            before = fingerprint('negative_before_' + name, ['core', 'mart'])
            run('inject_' + name, psql, sql)
            bad = build('negative_' + name + '_build', required=False)
            assert bad.returncode == 3, (name, bad.returncode)
            assert diagnostic in bad.stderr, (name, bad.stderr[-1000:])
            after = fingerprint('negative_after_' + name, ['core', 'mart'])
            assert before == after, name + ': failed build changed committed model'
            summary['negatives'][name] = dict(status='rejected_and_rolled_back', expected_diagnostic=diagnostic,
                                              before_fingerprint=before, after_fingerprint=after,
                                              evidence='logs/negative_' + name + '_build.log')
        summary['status'] = 'pass'
    except Exception as exc:
        summary.update(status='fail', error=repr(exc))
        raise
    finally:
        if started:
            stopped = run('stop_own_server', [PGBIN / 'pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'], required=False)
            summary['own_server_stopped'] = stopped.returncode == 0
            if stopped.returncode:
                summary['status'] = 'fail'
        if (runtime / 'server.log').exists():
            shutil.copyfile(runtime / 'server.log', out / 'server.log')
        temp_code.cleanup()
        if not started or summary.get('own_server_stopped'):
            temp_server.cleanup()
            summary['private_runtime_removed'] = True
        else:
            # Preserve failed-stop runtime instead of deleting a running server's files.
            temp_server._finalizer.detach()
            summary['private_runtime_preserved'] = str(runtime)
        summary['utc_end'] = datetime.now(timezone.utc).isoformat()
        dump(out / 'commands.json', commands)
        dump(out / 'summary.json', summary)
    print(json.dumps(dict(status=summary['status'], baseline=summary['baseline'],
                          mutation_kills=len(summary['mutations']), negatives=len(summary['negatives']), output=str(out))))


if __name__ == '__main__':
    main()
