#!/usr/bin/env python3
"""Only private socket PG16 + small synthetic data. No Olist/server installs.
Usage: python3 tests/model/history/verify-small-pg16.py EVIDENCE_DIRECTORY
Evidence excludes runtime/dependencies; own server is always stopped/removed.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(sys.argv[1]).resolve()
EVIDENCE.mkdir(parents=True, exist_ok=False)
PG = Path('/opt/homebrew/opt/postgresql@16/bin')
VERSION = subprocess.check_output([PG / 'postgres', '--version'], text=True).strip()
if ' 16.' not in VERSION:
    raise SystemExit('Existing PG16 required')
SUMMARY = dict(scope='small synthetic PG16 only', server=VERSION,
               at_utc=datetime.now(timezone.utc).isoformat(), checks={},
               full_olist='not_run_guard78', production='not_accessed',
               transport='private_unix_socket_no_tcp', shared_buffers='16MB', max_connections=5)
SUMMARY['files_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for directory in ('model', 'tests/model/history') for p in sorted((ROOT / directory).rglob('*'))
    if p.is_file() and p.suffix in ('.sql', '.py') and 'evidence' not in p.relative_to(ROOT).parts}
for path in sorted((ROOT / 'answers').rglob('*.sql')):
    SUMMARY['files_sha256'][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
for name in ('scripts/build-model.sh','scripts/init/02_raw_ddl.sql','tests/model/fixtures/base.sql',
             'tests/model/fixtures/assert-base.sql','tests/model/rollback.sql','tests/model/fingerprint.sql',
             'answers/q06-q10/test_fixture.py'):
    SUMMARY['files_sha256'][name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
SUMMARY['published_base'] = 'aab62d7a59f196be051df12466fb21c0da4659b9'
started = False
with tempfile.TemporaryDirectory(prefix='rwb-hist-', dir='/tmp') as runtime_name:
    runtime = Path(runtime_name)
    data, socket = runtime / 'data', runtime / 'socket'
    socket.mkdir()
    env = dict(os.environ)
    for key in list(env):
        if key.startswith('PG') or key in ('DATABASE_URL', 'RWB_REPORT_RELEASE'):
            env.pop(key, None)
    env.update(PGHOST=str(socket), PGPORT='55483', PGUSER='history_fixture',
               PGDATABASE='history_fixture', PGOPTIONS='', PGCONNECT_TIMEOUT='5',
               RWB_RAW_RELOAD_PAUSED='1', RWB_DB_MODE='host',
               PATH=str(PG) + os.pathsep + env['PATH'])

    def run(name, argv, *, stdin=None, expected=0, release=None, database=None):
        cfg = env.copy()
        if release:
            cfg['RWB_REPORT_RELEASE'] = release
        if database:
            cfg['PGDATABASE'] = database
        result = subprocess.run([str(a) for a in argv], cwd=ROOT, env=cfg, input=stdin,
                                text=True, capture_output=True, timeout=50)
        (EVIDENCE / (name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode != expected:
            raise RuntimeError(f'{name}: exit {result.returncode}, expected {expected}; see log')
        SUMMARY['checks'][name] = dict(status='pass', exit_code=result.returncode)
        return result.stdout

    PSQL = [PG / 'psql', '-X', '-w', '-v', 'ON_ERROR_STOP=1', '-P', 'pager=off']

    def sql(name, text, **kwargs):
        return run(name, PSQL + ['-1', '-qAt'], stdin=text, **kwargs).strip()

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        SUMMARY['checks'][name] = dict(status='pass')

    def reject(name, text, message):
        run(name, PSQL + ['-1'], stdin=text, expected=3)
        check(name + '_expected_error', message in (EVIDENCE / (name + '.log')).read_text())

    def build(name, release=None, **kwargs):
        return run(name, ['bash', 'scripts/build-model.sh', 'build'], release=release, **kwargs)

    def fingerprint(name, **kwargs):
        return run(name, PSQL + ['-qAt', '-F', '\t', '-f', 'tests/model/fingerprint.sql'], **kwargs)

    def raw_hash(name):
        return sql(name, "SELECT history.digest(jsonb_agg(to_jsonb(s) ORDER BY source_table,row_hash)) FROM history.source_rows() s")

    def history_hash(name):
        tables = ('schema_version','baseline_snapshot','baseline_product','category_event',
                  'report_release','release_source_row','report_binding','release_category','initial_release','report_result')
        query = ' UNION ALL '.join("SELECT '"+t+"' AS name,history.digest(coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text COLLATE \"C\"),'[]')) AS digest FROM history."+t+" t" for t in tables)
        return sql(name, "SET TimeZone='UTC'; SELECT history.digest(jsonb_agg(to_jsonb(t) ORDER BY name)) FROM ("+query+") t")

    def totals(name):
        return sql(name, "SELECT category_key, sum(price) FROM mart.v_order_items GROUP BY 1 ORDER BY 1")

    def append(ident, seller, category, boundary, *, product='P', action='set', correction=None, policy=False):
        # Fixture identifiers below are constants; SQL literals are explicitly escaped.
        lit = lambda x: 'NULL' if x is None else "'" + str(x).replace("'", "''") + "'"
        values = [ident, product, seller, action, category, None if policy else boundary,
                  boundary if policy else None, 'source_naive_purchase_v1' if boundary else None,
                  correction]
        return 'SELECT history.append_event(' + ','.join(map(lit, values)) + ",'{\"source\":\"synthetic-test\"}'::jsonb);"

    def release(ident, kind, parent, events, closed='2018-01-13'):
        array = "ARRAY[" + ','.join("'"+x+"'" for x in events) + "]::text[]"
        return f"SELECT history.create_release('{ident}','{kind}','{parent}',{array},timestamp '{closed}');"

    def add_order(ident, seller, at, price, state='MG', zip_prefix='30000'):
        return f"""
        INSERT INTO raw.customers(customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state)
            VALUES('c-{ident}','buyer','{zip_prefix}','city-{ident}','{state}');
        INSERT INTO raw.orders(order_id,customer_id,order_status,order_purchase_timestamp)
            VALUES('{ident}','c-{ident}','delivered','{at}');
        INSERT INTO raw.order_items(order_id,order_item_id,product_id,seller_id,price,freight_value)
            VALUES('{ident}','1','P','{seller}','{price}','0');
        """

    try:
        run('initdb', [PG / 'initdb', '-D', data, '-U', 'history_fixture', '-A', 'trust', '--no-locale', '--encoding=UTF8'])
        run('start', [PG / 'pg_ctl', '-D', data, '-l', runtime / 'server.log', '-w', '-o',
            f"-F -h '' -k {socket} -p 55483 -c shared_buffers=16MB -c max_connections=5 -c work_mem=1MB -c max_parallel_workers=0", 'start'])
        started = True
        run('create_lifecycle_db', [PG / 'createdb', 'lifecycle_fixture'])
        raw_ddl = 'CREATE SCHEMA raw;\n' + (ROOT / 'scripts/init/02_raw_ddl.sql').read_text()
        run('load_lifecycle', PSQL + ['-1'], stdin=raw_ddl + (ROOT / 'tests/model/fixtures/base.sql').read_text(), database='lifecycle_fixture')
        raw_before_bootstrap = fingerprint('lifecycle_raw_before_bootstrap',database='lifecycle_fixture')
        build('lifecycle_clean', database='lifecycle_fixture')
        first = fingerprint('lifecycle_first', database='lifecycle_fixture')
        check('bootstrap_raw_unchanged_exact', [x for x in raw_before_bootstrap.splitlines() if x.startswith('raw.')] == [x for x in first.splitlines() if x.startswith('raw.')])
        build('lifecycle_rebuild', database='lifecycle_fixture')
        second = fingerprint('lifecycle_second', database='lifecycle_fixture')
        check('lifecycle_idempotent', first == second)
        run('lifecycle_assertions', PSQL + ['-1', '-f', 'tests/model/fixtures/assert-base.sql'], database='lifecycle_fixture')
        run('lifecycle_late_failure', PSQL + ['-1', '-f', 'tests/model/rollback.sql'], expected=3, database='lifecycle_fixture')
        check('lifecycle_intended_failure', 'W11_INJECTED_LATE_FAILURE_AFTER_ALL_CHECKS' in (EVIDENCE / 'lifecycle_late_failure.log').read_text())
        check('lifecycle_rollback', second == fingerprint('lifecycle_after_rollback', database='lifecycle_fixture'))
        run('q1_q10_answers', ['bash', 'scripts/build-model.sh', 'answers'], database='lifecycle_fixture')
        run('generic_checks', ['bash', 'scripts/build-model.sh', 'check'], database='lifecycle_fixture')
        # Reuse the published 16-order behavioral assertions unchanged. Adapt only
        # their pre-history stage loader in memory, preserving their __file__ paths.
        run('create_q6_db', [PG / 'createdb', 'q6_q10_fixture'])
        source_path = ROOT / 'answers/q06-q10/test_fixture.py'
        source = source_path.read_text()
        anchor = "for stage in ('model/10_dims.sql', 'model/20_facts.sql'"
        adapted = "for stage in ('model/history/01_source.sql', 'model/history/02_prepare.sql', 'model/10_dims.sql', 'model/history/03_versions.sql', 'model/20_facts.sql'"
        check('q6_loader_anchor_unique', source.count(anchor) == 1)
        loader = "from pathlib import Path\np=Path('answers/q06-q10/test_fixture.py').resolve()\ns=p.read_text().replace(" + repr(anchor) + ',' + repr(adapted) + ")\nexec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})\n"
        run('published_q6_q10_assertions', [sys.executable, '-c', loader], database='q6_q10_fixture')

        run('create_history_db', [PG / 'createdb', 'history_fixture'])
        fixture = """
        INSERT INTO raw.products(product_id,product_category_name) VALUES('P','A');
        INSERT INTO raw.sellers(seller_id) VALUES('S1'),('S2');
        INSERT INTO raw.product_category_translation VALUES('A','alpha',NULL,now()),('B','beta',NULL,now()),('C','gamma',NULL,now());
        """ + add_order('old1','S1','2018-01-05 00:00:00',100,'SP','01000') + add_order('old2','S2','2018-01-05 00:00:00',200,'RJ','20000')
        run('load_history', PSQL + ['-1'], stdin=raw_ddl+fixture)
        check('private_server_settings', sql('server_settings', "SELECT current_setting('listen_addresses')='',current_setting('shared_buffers'),current_setting('max_connections')") == 't|16MB|5')
        build('bootstrap_R0')
        r0 = fingerprint('R0_first')
        baseline_raw = raw_hash('R0_raw_before')
        original_bindings = sql('original_bindings', "SELECT order_id,version_id,attribution_basis FROM history.report_binding WHERE release_id='original-v1' ORDER BY 1")
        check('baseline_time_unknown', sql('baseline_unknown_time', "SELECT bool_and(business_valid_from IS NULL AND basis='snapshot_at_bootstrap') FROM history.baseline_snapshot") == 't')
        check('R0_total', totals('R0_totals') == 'pt:A|300')
        reject('self_correction', append('self-cycle','S1','pt:B','2018-01-10',correction='self-cycle'), 'query returned no rows')
        sql('append_E1', append('E1','S1','pt:B','2018-01-10'))
        sql('retry_E1', append('E1','S1','pt:B','2018-01-10'))
        reject('event_conflict', append('E1','S1','pt:C','2018-01-10'), 'Conflicting event identity')
        check('event_retry_one_row', sql('event_count', 'SELECT count(*) FROM history.category_event') == '1')
        build('R0_after_event')
        check('R0_stable_after_event_rebuild', r0 == fingerprint('R0_after'))
        check('R0_raw_unchanged', baseline_raw == raw_hash('R0_raw_after'))
        sql('new_orders_and_profile_context', add_order('new1','S1','2018-01-12 00:00:00',30) + add_order('new2','S2','2018-01-12 00:00:00',40))
        before_R1 = raw_hash('R1_raw_before')
        sql('create_R1', release('R1','extension','original-v1',['E1']))
        sql('retry_R1', release('R1','extension','original-v1',['E1']))
        reject('release_conflict', release('R1','restatement','original-v1',['E1']), 'Conflicting release identity')
        build('build_R1','R1')
        r1 = fingerprint('R1_first')
        r1_source = history_hash('R1_source_first')
        check('seller_isolation', totals('R1_totals') == 'pt:A|340\npt:B|30')
        check('old_original_bindings_inherited', sql('inherited_bindings', "SELECT order_id,version_id,attribution_basis FROM history.report_binding WHERE release_id='R1' AND order_id LIKE 'old%' ORDER BY 1") == original_bindings)
        check('address_preservation', sql('addresses', "SELECT order_id,customer_state,customer_city,customer_zip_code_prefix FROM core.fact_order ORDER BY 1") == 'new1|MG|city-new1|30000\nnew2|MG|city-new2|30000\nold1|SP|city-old1|01000\nold2|RJ|city-old2|20000')
        build('R1_rebuild','R1')
        check('R1_rebuild_exact', r1 == fingerprint('R1_second'))
        check('persistent_source_rebuild_exact', r1_source == history_hash('R1_source_second'))
        check('R1_raw_unchanged', before_R1 == raw_hash('R1_raw_after'))
        # Assert real boundary and fallback behavior using the SQL resolver.
        check('half_open_boundary', sql('boundary', "SELECT category_key FROM history.resolve_category((SELECT baseline_id FROM history.report_release WHERE release_id='R1'),ARRAY['E1'],'P','S1','2018-01-09 23:59:59.999999') UNION ALL SELECT category_key FROM history.resolve_category((SELECT baseline_id FROM history.report_release WHERE release_id='R1'),ARRAY['E1'],'P','S1','2018-01-10')") == 'pt:A\npt:B')
        sql('append_correction', append('E2','S1','pt:B','2018-01-04',correction='E1'))
        build('R1_after_correction','R1')
        check('original_stable_after_correction', r1 == fingerprint('R1_after_correction_fp'))
        sql('create_restatement', release('R1-restated','restatement','R1',['E1','E2']))
        build('build_restatement','R1-restated')
        check('restatement_differs', totals('restated_totals') == 'pt:A|240\npt:B|130')
        check('default_original_never_advanced', sql('default_release', 'SELECT release_id FROM history.initial_release') == 'original-v1')
        reject('incomplete_correction', release('bad-chain','restatement','R1',['E2']), 'Incomplete correction chain')
        reject('missing_event', release('bad-event','restatement','R1',['missing']), 'Missing event in pinned set')
        reject('correction_scope', append('bad-scope','S2','pt:B','2018-01-04',correction='E2'), 'Correction scope mismatch')
        reject('correction_fork', append('bad-fork','S1','pt:B','2018-01-03',correction='E1'), 'duplicate key value')
        reject('missing_clock', "SELECT history.append_event('no-clock','P',NULL,'set','pt:C','2018-01-01',NULL,NULL,NULL,'{\"source\":\"test\"}')", 'violates check constraint')
        for event_sql in [append('E3',None,'pt:C','2018-01-21'), append('E4','S1',None,'2018-01-23',action='unset_override'), append('E5','S2','pt:D','2018-01-25',policy=True), append('E6','S2','unknown','2018-01-27'), append('E7',None,'pt:A','2018-01-28')]:
            sql('append_' + event_sql.split("'")[1], event_sql)
        active = "ARRAY['E1','E2','E3','E4','E5','E6','E7']"
        resolver = f"history.resolve_category((SELECT baseline_id FROM history.report_release WHERE release_id='R1'),{active},'P',v.seller,v.at::timestamp)"
        scopes = sql('scope_unset_policy_unknown_return', f"SELECT v.id,r.category_key,r.attribution_basis,r.version_id FROM (VALUES (1,'S1','2018-01-22'),(2,'S2','2018-01-22'),(3,'S1','2018-01-23'),(4,'S2','2018-01-24'),(5,'S2','2018-01-25'),(6,'S2','2018-01-27'),(7,'S1','2018-01-28')) v(id,seller,at) CROSS JOIN LATERAL {resolver} r ORDER BY v.id")
        values = [x.split('|')[1:3] for x in scopes.splitlines()]
        check('product_seller_unset_observed_unknown_return', values == [['pt:B','asserted_valid_time'],['pt:C','asserted_valid_time'],['pt:C','asserted_valid_time'],['pt:C','asserted_valid_time'],['pt:D','observed_since_policy'],['unknown','asserted_valid_time'],['pt:A','asserted_valid_time']])
        check('return_A_new_identity', scopes.splitlines()[-1].split('|')[-1] not in original_bindings)
        sql('observation_no_business_clock', append('observation-only','S2','pt:Z',None))
        check('untimed_observation_not_applied', sql('no_invented_asof', "SELECT category_key,attribution_basis FROM history.resolve_category((SELECT baseline_id FROM history.report_release WHERE release_id='R1'),ARRAY['observation-only'],'P','S2','2018-01-30')") == 'pt:A|snapshot_at_bootstrap')
        sql('ambiguous_event', append('ambiguous',None,'pt:B','2018-01-21'))
        reject('ambiguous_release', release('bad-ambiguity','restatement','R1',['E3','ambiguous']), 'Ambiguous category boundary')
        reject('sealed_binding_insert', "INSERT INTO history.report_binding SELECT release_id,'impossible',order_item_id,product_id,seller_id,source_item_sha256,version_id,category_key,attribution_basis,baseline_id,event_id FROM history.report_binding WHERE release_id='R1' LIMIT 1", 'release is sealed')
        reject('immutable_event', "UPDATE history.category_event SET category_key='pt:C' WHERE event_id='E1'", 'history source is immutable')
        reject('immutable_release', "DELETE FROM history.report_release WHERE release_id='R1'", 'history source is immutable')
        # Event categories/versions no longer in current raw product still build.
        sql('create_all_events', release('R-policy','restatement','R1',['E1','E2','E3','E4','E5','E6','E7']))
        build('all_events_build','R-policy')
        check('retained_event_category_domain', sql('D_domain', "SELECT count(*) FROM core.dim_category WHERE category_key='pt:D' AND name_en IS NULL") == '1')
        # Cold restore retains all source/history but zero derived core/mart data.
        build('R1_before_backup','R1')
        before_restore = fingerprint('before_cold_restore')
        check('original_after_restatement_stable', r1 == before_restore)
        before_late_source = history_hash('source_before_late_failure')
        backup = run('dump_raw_and_history', [PG / 'pg_dump', '--no-owner', '--no-acl', '--schema=raw', '--schema=history'])
        (EVIDENCE / 'synthetic-source-restore.sql').write_text(backup)
        run('create_restore_db', [PG / 'createdb', 'history_restore'])
        run('restore_sources', PSQL + ['-1'], stdin=backup, database='history_restore')
        check('restore_has_no_projections', sql('restore_empty_core', "SELECT count(*) FROM pg_namespace WHERE nspname IN ('core','mart')", database='history_restore') == '0')
        build('cold_rebuild_R1','R1',database='history_restore')
        check('cold_restore_exact_result', before_restore == fingerprint('cold_restored_fingerprint',database='history_restore'))
        # Exercise all temporal branches through the complete model on the restored
        # clone; original R1 raw generation in the other DB remains unchanged.
        future_values = [(1,'S1','22'),(2,'S2','22'),(3,'S1','23'),(4,'S2','24'),(5,'S2','25'),(6,'S2','27'),(7,'S1','28')]
        sql('future_items_restore_clone', ''.join(add_order('future'+str(i),seller,'2018-01-'+day+' 00:00:00',1) for i,seller,day in future_values), database='history_restore')
        future_events = ['E1','E2','E3','E4','E5','E6','E7']
        sql('future_release_restore_clone', release('R-future','extension','R-policy',future_events,'2018-01-29'), database='history_restore')
        build('future_full_model','R-future',database='history_restore')
        future_actual = sql('future_item_bindings', "SELECT order_id,mart.v_order_items.category_key,attribution_basis FROM mart.v_order_items JOIN core.dim_category_version ON category_version_id=version_id WHERE order_id LIKE 'future%' ORDER BY 1", database='history_restore')
        check('integrated_future_scope_unset_policy_unknown_return', [x.split('|')[1:] for x in future_actual.splitlines()] == values)
        reject('late_taxonomy_extension', "INSERT INTO raw.product_category_translation(product_category_name,product_category_name_english) VALUES('D','delta');" + release('taxonomy-change','extension','R-policy',future_events), 'Extension changed parent taxonomy')
        # SQL error after all stages/checks must roll back model + newly pinned result.
        rollback_sql = (ROOT / 'tests/model/rollback.sql').read_text().replace('\\ir ../../model/build.sql', '\\ir model/build.sql')
        rollback_sql = rollback_sql.replace('SET LOCAL capibara.raw_reload_paused', "SET LOCAL capibara.report_release='R1';\nSET LOCAL capibara.raw_reload_paused")
        rollback_sql = rollback_sql.replace("capibara.report_release='R1'", "capibara.report_release='rollback-candidate'")
        rollback_sql = rollback_sql.replace('\\ir model/build.sql', release('rollback-candidate','restatement','R1',['E1','E2']) + '\n\\ir model/build.sql')
        run('history_late_failure', PSQL + ['-1'], stdin=rollback_sql, expected=3)
        check('history_intended_failure', 'W11_INJECTED_LATE_FAILURE_AFTER_ALL_CHECKS' in (EVIDENCE / 'history_late_failure.log').read_text())
        check('history_late_failure_rollback', before_restore == fingerprint('after_history_rollback'))
        check('persistent_source_late_rollback_exact', before_late_source == history_hash('source_after_late_failure'))
        check('candidate_source_and_result_rolled_back', sql('no_rollback_candidate', "SELECT (SELECT count(*) FROM history.report_release WHERE release_id='rollback-candidate')+(SELECT count(*) FROM history.report_binding WHERE release_id='rollback-candidate')+(SELECT count(*) FROM history.report_result WHERE release_id='rollback-candidate')") == '0')
        reject('category_invariant_mutation', "UPDATE core.fact_order_item SET category_version_id=(SELECT version_id FROM core.dim_category_version WHERE category_key='pt:B') WHERE order_id='old1'; SELECT history.check_model();", 'Model category binding mismatch')
        check('mutation_rolled_back', before_restore == fingerprint('after_mutation_rollback'))
        reject('context_drift', "UPDATE raw.customers SET customer_state='XX' WHERE customer_id='c-old1'; SELECT history.assert_release('R1');", 'Raw generation differs')
        check('address_mutation_rolled_back', before_restore == fingerprint('after_address_mutation_rollback'))
        reject('corrupt_event_source', "ALTER TABLE history.category_event DISABLE TRIGGER history_no_mutation; UPDATE history.category_event SET category_key='pt:X' WHERE event_id='E1'; SELECT history.assert_source();", 'Event source digest mismatch')
        reject('corrupt_baseline_source', "ALTER TABLE history.baseline_product DISABLE TRIGGER history_no_mutation; UPDATE history.baseline_product SET category_key='pt:X'; SELECT history.assert_source();", 'Baseline source digest mismatch')
        check('source_corruption_rolled_back', before_late_source == history_hash('source_after_corruption_tests'))
        reject('late_payment_extension', "INSERT INTO raw.order_payments(order_id,payment_sequential,payment_value) VALUES('old1','1','100');" + release('late-payment','extension','R1',['E1','E2']), 'in closed period requires restatement')
        reject('late_empty_order_extension', "INSERT INTO raw.orders(order_id,customer_id,order_status,order_purchase_timestamp) VALUES('empty-late','c-old1','canceled','2018-01-05');" + release('late-empty','extension','R1',['E1','E2']), 'in closed period requires restatement')
        sql('insert_late_item', add_order('late','S1','2018-01-05 00:00:00',7))
        late_raw = raw_hash('late_raw_before')
        reject('late_extension', release('late-extension','extension','R1',['E1','E2']), 'in closed period requires restatement')
        # Model default R0 rejects newer raw before DROP; no silent rebootstrap.
        run('old_release_raw_mismatch', ['bash','scripts/build-model.sh','build'], expected=3, release='R1')
        check('old_release_expected_error', 'Raw generation differs from pinned release R1' in (EVIDENCE / 'old_release_raw_mismatch.log').read_text())
        # Existing committed model survives even though source was intentionally extended.
        after_mismatch = fingerprint('after_raw_mismatch')
        check('mismatch_model_survives', [x for x in before_restore.splitlines() if not x.startswith('raw.')] == [x for x in after_mismatch.splitlines() if not x.startswith('raw.')])
        sql('create_late_restatement', release('R-late','restatement','R1',['E1','E2']))
        build('build_late_restatement','R-late')
        check('late_restatement_only', totals('late_restatement_totals') == 'pt:A|240\npt:B|137')
        check('late_raw_unchanged_by_build', late_raw == raw_hash('late_raw_after'))
        check('no_failed_release_rows', sql('no_failed_releases', "SELECT count(*) FROM history.report_release WHERE release_id LIKE 'bad-%' OR release_id='late-extension'") == '0')
        check('old_bindings_still_present', sql('original_bindings_final', "SELECT order_id,version_id,attribution_basis FROM history.report_binding WHERE release_id='original-v1' ORDER BY 1") == original_bindings)
        expected_fields = {
            'q06_price_history': 'population,product_id,distinct_prices,units_with_unknown_price,purchase_date,price,units_sold',
            'q07_delivery_by_state': 'population,customer_state,late_basis,orders_count,duration_denominator,avg_delivery_days,late_denominator,late_orders,late_pct',
            'q08_status_snapshot': 'order_status,orders_count,orders_pct,orders_without_items',
            'q09_payments_2018_by_state': 'customer_state,payment_count,amount_denominator,payment_amount,known_payment_amount_sum,installments_denominator,avg_installments_all_types,credit_installments_denominator,avg_installments_credit_card',
            'q09_payment_methods': 'period,payment_type,payment_count,installments_denominator,avg_installments',
            'q10_review_delivery': 'population,score_policy,late_basis,review_score,orders_count,duration_denominator,avg_delivery_days,late_denominator,late_orders,late_pct',
            'q10_review_coverage': 'population,orders_count,orders_without_score,orders_with_multiple_scores,orders_in_multiple_valid_score_groups,orders_with_out_of_range_score',
        }
        actual_fields = sql('frontend_fields', "SELECT table_name,string_agg(column_name,',' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_schema='mart' AND table_name LIKE 'q%' GROUP BY 1 ORDER BY 1")
        actual_fields = dict(x.split('|',1) for x in actual_fields.splitlines())
        check('seven_frontend_relations_fields_compatible', all(actual_fields[k] == v for k,v in expected_fields.items()))
        run('final_answers', ['bash','scripts/build-model.sh','answers'])
        run('final_checks', ['bash','scripts/build-model.sh','check'])
        SUMMARY['status'] = 'pass'
    except Exception as exc:
        SUMMARY.update(status='fail',error=str(exc))
        raise
    finally:
        if started:
            run('stop_own_server', [PG / 'pg_ctl','-D',data,'-m','fast','-w','stop'])
        SUMMARY['runtime_removed_on_exit'] = True
        (EVIDENCE / 'summary.json').write_text(json.dumps(SUMMARY,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=SUMMARY['status'],checks=len(SUMMARY['checks']),evidence=str(EVIDENCE))))
