#!/usr/bin/env python3
"""Small standard-library checks of W-10 deliverables; no database access."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
paths = [ROOT / "model/40_mart.sql", ROOT / "model/50_answers.sql", ROOT / "docs/metric-definitions.md"]
paths.extend(p for p in sorted((ROOT / "answers").iterdir()) if p.is_file())
for path in paths:
    source = path.read_text()
    assert source.endswith("\n"), f"Missing final newline: {path}"
    for number, line in enumerate(source.splitlines(), 1):
        assert line == line.rstrip(), f"Trailing whitespace: {path}:{number}"
    if path.suffix == ".py":
        compile(source, str(path), "exec")
    elif path.suffix == ".json":
        json.loads(source)
    elif path.suffix == ".md":
        for target in re.findall(r"\]\(([^)]+)\)", source):
            if "://" not in target:
                assert (path.parent / target.split("#")[0]).exists(), f"Broken link: {path}: {target}"

report = json.loads((ROOT / "answers/verification.json").read_text())
assert report["status"] == "offline_only" and report["postgresql_executed"] is False
for relative, digest in report["checked_file_sha256"].items():
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, f"Stale offline evidence: {relative}"
checksum_path = ROOT / "answers/sha256.json"
if checksum_path.exists():
    checksums = json.loads(checksum_path.read_text())
    for relative, digest in checksums["files"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, f"Stale handoff: {relative}"
print(f"static_only: Python syntax, JSON, whitespace, relative links and evidence hashes OK ({len(paths)} files); no DB executed")
