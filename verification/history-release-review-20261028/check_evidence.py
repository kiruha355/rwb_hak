#!/usr/bin/env python3
"""Read-only audit of release runner input manifest in this checkout."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
summary_path = root / 'docs/phase-20261028/evidence/release-pg16/summary.json'
summary = json.loads(summary_path.read_text())
manifest = summary['files_sha256']
inputs = [f'answers/q06-q10/{name}.sql' for name in ('q06', 'q07', 'q08', 'q09', 'q10', 'q10_coverage')]
print('summary:', summary_path.relative_to(root))
print('run:', summary['at_utc'], 'status:', summary['status'], 'checks:', len(summary['checks']))
print('listed mismatches:', sum(hashlib.sha256((root / p).read_bytes()).hexdigest() != h for p, h in manifest.items()))
for p in inputs:
    digest = hashlib.sha256((root / p).read_bytes()).hexdigest()
    print(f'{p} sha256={digest} in_run_manifest={p in manifest}')
