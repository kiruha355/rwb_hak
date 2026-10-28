"""Normalize research records without treating researcher confidence as validation."""
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'catalog'
OUT.mkdir(exist_ok=True)
records, operations = [], []
errors = []
for stage in ('orientation', 'corpus'):
    for folder in sorted((BASE / stage).iterdir()):
        if not folder.is_dir():
            continue
        for name, dest in [('findings.jsonl', records), ('search-log.jsonl', operations)]:
            path = folder / name
            if not path.exists():
                errors.append(str(path.relative_to(BASE)))
                continue
            for line, raw in enumerate(path.read_text().splitlines(), 1):
                if not raw.strip():
                    continue
                obj = json.loads(raw)
                obj['_source_file'] = str(path.relative_to(BASE))
                obj['_source_line'] = line
                obj['_stage'] = stage
                obj['_package'] = folder.name
                if name == 'findings.jsonl':
                    obj['_validation'] = 'candidate_not_independently_accepted'
                dest.append(obj)
ids = [x['finding_id'] for x in records]
assert len(ids) == len(set(ids)), 'duplicate finding ids'
for name, rows in [('all-findings.jsonl', records), ('search-operations.jsonl', operations)]:
    (OUT / name).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))
summary = {
    'findings_total': len(records),
    'findings_by_stage': dict(Counter(x['_stage'] for x in records)),
    'findings_by_package': dict(Counter(x['_package'] for x in records)),
    'logged_operations_total': len(operations),
    'logged_operations_by_stage': dict(Counter(x['_stage'] for x in operations)),
    'language_labels': dict(Counter(str(x.get('language', 'unspecified')) for x in operations)),
    'finding_source_types': dict(Counter(str(x.get('source_type')) for x in records)),
    'distinct_finding_urls': len({x.get('url') for x in records if x.get('url')}),
    'distinct_http_finding_urls': len({x['url'] for x in records if urlparse(x.get('url', '')).scheme in ('http', 'https')}),
    'corpus_http_finding_urls': len({x['url'] for x in records if x['_stage'] == 'corpus' and urlparse(x.get('url', '')).scheme in ('http', 'https')}),
    'finding_domains': dict(Counter(urlparse(x.get('url', '')).netloc for x in records)),
    'missing_files': errors,
    'limits': ['Counts describe records and logged operations, not independent proofs',
               'No acceptance inherited from self-reported confidence or primary flag',
               'No universal internet coverage; query and source gaps remain explicit']}
review_by_id = {}
review_count = 0
for p in sorted((BASE / 'reviews').glob('*/decisions.jsonl')):
    for raw in p.read_text().splitlines():
        if raw.strip():
            d = json.loads(raw)
            d['_review_file'] = str(p.relative_to(BASE))
            review_by_id.setdefault(d['finding_id'], []).append(d)
            review_count += 1
summary['review_decision_records'] = review_count
summary['findings_with_explicit_review'] = len(review_by_id)
summary['findings_without_explicit_review'] = sorted(set(ids) - set(review_by_id))
(OUT / 'coverage-counts.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
(OUT / 'review-matrix.jsonl').write_text(''.join(json.dumps({
    'finding_id': r['finding_id'], 'source_file': r['_source_file'],
    'review_positions': review_by_id.get(r['finding_id'], []),
    'interpretation': 'Evidence and recommendation direction must be separated; no majority-vote acceptance'
}, ensure_ascii=False) + '\n' for r in records))
lines = ['# Source → finding → task → acceptance check', '',
         'Candidate matrix. All checks retain proposed/executed scope of source record.', '',
         '| Finding | Source | Task | Acceptance check |', '|---|---|---|---|']
def cell(value):
    return str(value if value is not None else 'unresolved').replace('|', '\\|').replace('\n', ' ')
for r in records:
    if r['_stage'] != 'corpus':
        continue
    lines.append('| ' + ' | '.join(cell(x) for x in [r['finding_id'], r.get('url'), r.get('task'), r.get('acceptance_check')]) + ' |')
(OUT / 'task-matrix.md').write_text('\n'.join(lines) + '\n')
print(json.dumps(summary, ensure_ascii=False))
