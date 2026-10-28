#!/usr/bin/env python3
"""Deterministic, offline manifest of the eight CSV inputs; never loads a DB."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "tests/model/input-manifest.lock.json"


class ManifestError(ValueError):
    pass


class HashReader(io.RawIOBase):
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.bytes = 0

    def readable(self):
        return True

    def readinto(self, target):
        n = self.stream.readinto(target)
        if n:
            self.digest.update(memoryview(target)[:n])
            self.bytes += n
        return n


def inspect_file(path, spec):
    """Hash the very byte stream parsed as CSV, including BOM and newlines."""
    csv.field_size_limit(16 * 1024 * 1024)
    with path.open("rb") as source:
        before = os.fstat(source.fileno())
        reader = HashReader(source)
        with io.TextIOWrapper(io.BufferedReader(reader), encoding="utf-8-sig", newline="") as text:
            rows = csv.reader(text, strict=True)
            header = next(rows, None)
            if header != spec["header"]:
                raise ManifestError(f"{path.name}: header {header!r}, expected {spec['header']!r}")
            count = 0
            for count, row in enumerate(rows, 1):
                if len(row) != len(header):
                    raise ManifestError(f"{path.name}: record {count}: {len(row)} fields, expected {len(header)}")
            after = os.fstat(source.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ManifestError(f"{path.name}: changed while reading")
    return {**spec, "sha256": reader.digest.hexdigest(), "bytes": reader.bytes, "rows": count}


def load_manifest(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ManifestError(f"{path}: unsupported manifest")
    files = value.get("files")
    if not isinstance(files, list) or len(files) != 8:
        raise ManifestError(f"{path}: expected exactly eight files")
    names = [f.get("file") for f in files if isinstance(f, dict)]
    if len(names) != 8 or len(set(names)) != 8 or any(not isinstance(n, str) or Path(n).name != n for n in names):
        raise ManifestError(f"{path}: duplicate or unsafe filename")
    return value


def collect(data_dir, pinned):
    files = [inspect_file(data_dir / spec["file"], spec) for spec in pinned["files"]]
    return {"schema_version": 1, "source": pinned["source"], "files": files}


def compare(actual, expected):
    failures = []
    for field in ("schema_version", "source"):
        if actual.get(field) != expected.get(field):
            failures.append(f"{field}: mismatch")
    left = {f["file"]: f for f in actual["files"]}
    right = {f["file"]: f for f in expected["files"]}
    for name in sorted(left.keys() | right.keys()):
        if name not in left or name not in right:
            failures.append(f"{name}: missing/extra manifest entry")
            continue
        for key in sorted(left[name].keys() | right[name].keys()):
            if left[name].get(key) != right[name].get(key):
                failures.append(f"{name}.{key}: actual={left[name].get(key)!r}, expected={right[name].get(key)!r}")
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--verify-pinned", action="store_true", help="fail unless exact pinned bytes/header/count match")
    parser.add_argument("--compare", type=Path, help="also compare with a previously generated manifest")
    parser.add_argument("--output", type=Path, help="write JSON here; otherwise stdout")
    args = parser.parse_args(argv)
    try:
        pinned = load_manifest(PIN)
        if args.output and (args.output.resolve() == PIN.resolve() or args.output.resolve() in {(args.data_dir / f["file"]).resolve() for f in pinned["files"]}):
            raise ManifestError("output must not overwrite the pin or an input CSV")
        actual = collect(args.data_dir, pinned)
        failures = compare(actual, pinned) if args.verify_pinned else []
        if args.compare:
            failures += compare(actual, load_manifest(args.compare))
        if failures:
            raise ManifestError("\n".join(failures))
        payload = json.dumps(actual, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
        print("CSV manifest checked; database/core not checked", file=sys.stderr)
        return 0
    except (OSError, ValueError, csv.Error, UnicodeError, KeyError, TypeError) as error:
        print(f"input-manifest: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
