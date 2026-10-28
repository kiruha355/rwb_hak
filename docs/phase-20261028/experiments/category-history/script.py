#!/usr/bin/env python3
"""Offline CSV audit + synthetic temporal experiment. No DB and no raw writes.

Run from any directory: python3 /path/to/category-history/script.py
Input bytes are pinned to the published baseline; outputs are deterministic.
"""
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MAIN = 'bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4'
REFS = [MAIN, '99bcbb366720f912ef6017a40aa5dbd6a671a8a4',
        'b0bd0200a0a88b6bb7eb242cfc11d3239ff0fb68']
BASELINE = 'research/internet-2026-10-28/orchestrator/evidence/sol-independent-check.json'
MODEL = ['model/00_schemas.sql', 'model/10_dims.sql', 'model/20_facts.sql',
         'model/40_mart.sql', 'model/build.sql']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def git(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rows(name):
    with (ROOT / 'data' / name).open(encoding='utf-8-sig', newline='') as f:
        yield from csv.DictReader(f)


def audit_csv(baseline):
    manifest = {}
    for name, spec in sorted(baseline['files'].items()):
        path = ROOT / 'data' / name
        digest = file_sha(path)
        count = sum(1 for _ in rows(name))
        with path.open(encoding='utf-8-sig', newline='') as f:
            header = next(csv.reader(f))
        manifest[name] = dict(sha256=digest, bytes=path.stat().st_size,
                              records=count, header=header,
                              baseline_sha256=spec['sha256'],
                              baseline_match=digest == spec['sha256'] and count == spec['records']
                              and header == spec['header'])
        assert manifest[name]['baseline_match'], f'Baseline drift: {name}'
    products = {r['product_id']: r['product_category_name'] or None
                for r in rows('olist_products_dataset.csv')}
    orders = {r['order_id']: (r['order_status'], r['order_purchase_timestamp'])
              for r in rows('olist_orders_dataset.csv')}
    sellers = defaultdict(set)
    pairs = Counter()
    revenues = defaultdict(Decimal)
    cat_revenues = defaultdict(Decimal)
    n = 0
    for r in rows('olist_order_items_dataset.csv'):
        n += 1
        p, s = r['product_id'], r['seller_id']
        sellers[p].add(s)
        pairs[p, s] += 1
        if orders[r['order_id']][0] == 'delivered':
            value = Decimal(r['price'])
            revenues[p, s] += value
            cat_revenues[products[p]] += value
    multi = sorted(p for p, ss in sellers.items() if len(ss) > 1)
    example = sorted(multi, key=lambda p: (-sum(pairs[p, s] for s in sellers[p]), p))[0]
    examples = []
    for r in rows('olist_order_items_dataset.csv'):
        if r['product_id'] == example and r['seller_id'] not in {x['seller_id'] for x in examples}:
            examples.append({k: r[k] for k in ('order_id', 'order_item_id', 'product_id', 'seller_id', 'price')})
            examples[-1]['purchase_timestamp'] = orders[r['order_id']][1]
    counts = dict(products=len(products), products_without_category=sum(v is None for v in products.values()),
                  item_rows=n, products_with_items=len(sellers), product_seller_pairs=len(pairs),
                  multi_seller_products=len(multi),
                  multi_seller_item_rows=sum(pairs[p, s] for p in multi for s in sellers[p]),
                  max_sellers_per_product=max(map(len, sellers.values())),
                  delivered_category_count=len(cat_revenues),
                  delivered_item_revenue=str(sum(cat_revenues.values())))
    assert counts['multi_seller_products'] == 1225
    assert counts['delivered_item_revenue'] == '13221498.11'
    counts['identity_example'] = dict(product_id=example, category=products[example],
        sellers=[dict(seller_id=s, item_rows=pairs[example, s],
                      delivered_item_revenue=str(revenues[example, s])) for s in sorted(sellers[example])],
        real_rows=examples,
        caveat='Observed product/seller pairs do not prove who owns category edits; no changes inferred.')
    return manifest, counts


def experiment():
    # Deliberately invented symbolic calendar, all prices Decimal; not Olist history.
    baseline = {'P': 'A'}
    events = []
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    def add(e):
        same = [x for x in events if x['id'] == e['id']]
        if same:
            if same[0] != e:
                raise ValueError('conflicting event ID')
            return  # exact retry is idempotent
        if e['supersedes']:
            prior = next(x for x in events if x['id'] == e['supersedes'])
            if (prior['product'], prior['seller']) != (e['product'], e['seller']):
                raise ValueError('correction scope mismatch')
            if e['known'] <= prior['known']:
                raise ValueError('correction knowledge order')
            if any(x['supersedes'] == prior['id'] for x in events):
                raise ValueError('concurrent correction branch')
        events.append(e.copy())

    def event(ident, known, effective, category, seller=None, action='set', supersedes=None):
        return dict(id=ident, known=known, effective=effective, category=category,
                    product='P', seller=seller, action=action, supersedes=supersedes)

    def resolve(item, cutoff):
        known = [e for e in events if e['known'] <= cutoff]
        replaced = {e['supersedes'] for e in known if e['supersedes']}
        active = [e for e in known if e['id'] not in replaced]
        for seller in (item['seller'], None):
            eligible = [e for e in active if e['product'] == item['product'] and e['seller'] == seller
                        and (e['effective'] if e['effective'] is not None else e['known']) <= item['at']]
            if eligible:
                def start(e):
                    return e['effective'] if e['effective'] is not None else e['known']
                max_start = max(map(start, eligible))
                winners = [e for e in eligible if start(e) == max_start]
                if len(winners) != 1:
                    raise ValueError('ambiguous effective-time claims')
                e = winners[0]
                if e['action'] == 'unset':
                    continue
                return dict(category=e['category'], version=e['id'],
                            basis='asserted_valid_time' if e['effective'] is not None else 'observed_since_policy')
        return dict(category=baseline[item['product']], version='baseline:P', basis='snapshot_at_bootstrap')

    def item(ident, seller, at, amount):
        return dict(id=ident, product='P', seller=seller, at=at, price=amount)

    old = [item('old-S1', 'S1', 5, '100'), item('old-S2', 'S2', 5, '200')]
    new = [item('new-S1', 'S1', 12, '30'), item('new-S2', 'S2', 12, '40')]

    def bind(items, cutoff):
        return [dict(item=x['id'], price=x['price'], **resolve(x, cutoff)) for x in items]

    def totals(bindings):
        out = defaultdict(Decimal)
        for b in bindings:
            out[b['category']] += Decimal(b['price'])
        return {k: str(v) for k, v in sorted(out.items())}

    r0 = bind(old, 9)
    frozen = canon(r0)
    e1 = event('E1', 10, 10, 'B', 'S1')
    add(e1)
    r1 = r0 + bind(new, 13)
    check('A_to_B_does_not_change_old_report', canon(r0) == frozen and totals(r0) == {'A': '300'})
    check('seller_override_does_not_change_other_seller', totals(r1) == {'A': '340', 'B': '30'})
    # Current-product join reclassifies all history: counterexample for existing design.
    current_product_join = {'B': str(sum(Decimal(x['price']) for x in old + new))}
    check('current_join_counterexample', current_product_join == {'B': '370'})
    add(e1)
    check('exact_event_retry_is_idempotent', len(events) == 1)
    try:
        add({**e1, 'category': 'X'})
    except ValueError:
        check('conflicting_duplicate_rejected', True)
    else:
        raise AssertionError('conflicting duplicate accepted')
    # At knowledge 20 a correction says S1's event started at 4, not 10.
    add(event('E2', 20, 4, 'B', 'S1', supersedes='E1'))
    restated = bind(old + new, 20)
    check('backdating_visible_only_in_new_restatement', totals(restated) == {'A': '240', 'B': '130'})
    check('old_cutoff_rebuild_stable_after_correction', canon(bind(old, 9)) == frozen)
    check('original_release_binding_still_stable', totals(r1) == {'A': '340', 'B': '30'})
    check('cold_replay_of_R1_with_pinned_cutoff', canon(bind(old + new, 13)) == canon(r1))
    check('half_open_boundary', resolve(item('before', 'S1', 3, '1'), 20)['category'] == 'A'
          and resolve(item('at', 'S1', 4, '1'), 20)['category'] == 'B')
    # A product default can evolve independently; override keeps precedence.
    add(event('E3', 21, 21, 'C'))
    check('product_and_seller_scopes_coexist',
          resolve(item('x', 'S1', 22, '1'), 22)['category'] == 'B'
          and resolve(item('y', 'S2', 22, '1'), 22)['category'] == 'C')
    add(event('E4', 23, 23, None, 'S1', action='unset'))
    check('unset_override_reveals_product_default', resolve(item('z', 'S1', 23, '1'), 23)['category'] == 'C')
    add(event('E5', 25, None, 'D', 'S2'))
    check('observation_does_not_invent_past_valid_time',
          resolve(item('before-observation', 'S2', 24, '1'), 26)['category'] == 'C'
          and resolve(item('after-observation', 'S2', 25, '1'), 26)['basis'] == 'observed_since_policy')
    add(event('E6', 27, 27, 'unknown', 'S2'))
    check('explicit_unknown_is_not_unset', resolve(item('u', 'S2', 27, '1'), 27)['category'] == 'unknown')
    add(event('RETURN_A', 28, 28, 'A'))
    check('return_to_baseline_has_new_version', resolve(item('return', 'S1', 28, '1'), 28)
          == dict(category='A', version='RETURN_A', basis='asserted_valid_time'))
    # Both implementations can preserve exact releases. Snapshot version stores these maps.
    snapshots = {'R0': json.loads(frozen), 'R1': json.loads(canon(r1))}
    check('immutable_snapshot_alternative_rebuilds_same_reports',
          totals(snapshots['R0']) == totals(r0) and totals(snapshots['R1']) == totals(r1))
    late = item('late-arrival', 'S1', 5, '7')
    r2_late = r1 + bind([late], 20)
    check('late_item_creates_new_release_without_changing_old',
          len(r1) == 4 and len(r2_late) == 5 and sha(canon(r0)) == sha(frozen))
    candidate = list(r1)
    try:
        candidate.append(dict(item='bad', price='1', category='NO_CATEGORY', version='bad', basis='bad'))
        assert all(b['category'] in {'A', 'B', 'C', 'D', 'unknown'} for b in candidate)
    except AssertionError:
        candidate = None
    check('simulated_failed_build_does_not_publish', candidate is None and totals(r1) == {'A': '340', 'B': '30'})
    add(event('E7', 28, 27, 'X', 'S2'))
    try:
        resolve(item('ambiguous', 'S2', 28, '1'), 28)
    except ValueError:
        check('equal_effective_time_ambiguity_rejected', True)
    else:
        raise AssertionError('ambiguous state accepted')
    return dict(scope='Synthetic stdlib model, not PostgreSQL/core, symbolic time units',
                baseline=baseline, events=events, items=old + new,
                R0=r0, R1=r1, restated_R1=restated,
                totals=dict(R0=totals(r0), R1=totals(r1), restated_R1=totals(restated),
                            incorrect_current_product_join=current_product_join),
                digests=dict(R0=sha(canon(r0)), R1=sha(canon(r1))),
                checks=checks, passed=len(checks),
                polling_counterexample={'true_states': ['A', 'B', 'A'],
                                        'polls': ['A', 'A'], 'lost_transition': 'B'})


def main():
    assert file_sha(HERE / 'tasks.source.md') == 'c24f3190729a672c09fcb97854a678fa02712456350038ff2bd738095652d1c5'
    baseline_bytes = git(MAIN, BASELINE)
    baseline = json.loads(baseline_bytes)
    manifest, counts = audit_csv(baseline)
    static = {}
    for path in MODEL:
        versions = {ref: sha(git(ref, path)) for ref in REFS}
        versions['working_tree'] = file_sha(ROOT / path)
        static[path] = versions
    simulation = experiment()
    unchanged = all(file_sha(ROOT / 'data' / name) == info['sha256'] for name, info in manifest.items())
    assert unchanged, 'CSV changed during experiment'
    result = dict(method='Streaming csv + compact key maps + Decimal + synthetic simulation; no core queries',
                  baseline=dict(ref=MAIN, path=BASELINE, sha256=sha(baseline_bytes)),
                  requirements=dict(ref='558f0f6a38110acc9fcf4386a7e53ece973aedf5',
                                    sha256=file_sha(HERE / 'tasks.source.md')),
                  script_sha256=file_sha(Path(__file__)), inputs=manifest,
                  csv_observations=counts, model_source_hashes=static,
                  simulation=simulation, csv_unchanged_after=unchanged,
                  limits=['No PostgreSQL execution', 'No historical Olist category versions',
                          'No performance benchmark', 'No DB-level privilege/concurrency/rollback proof'])
    (HERE / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(csv_counts=counts, simulation_totals=simulation['totals'],
                         passed=simulation['passed'], csv_unchanged_after=unchanged), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
