#!/usr/bin/env bash
# Read-only prerequisites and baseline check. Never starts or reloads anything.
set -euo pipefail

DEV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_MODE="${1:-runtime}"
case "$DEV_MODE" in
  --help|-h)
    echo "Usage: bash scripts/dev-check.sh [--offline]"
    echo "Default: local tools/CSV plus Docker/PostgreSQL/raw counts (read-only)."
    echo "--offline: local tools/CSV only; does not prove database readiness."
    echo "Exit codes: 0 selected checks passed; 2 local prerequisite; 3 runtime unavailable."
    exit 0 ;;
  --offline) ;;
  runtime) ;;
  *) echo "Unknown option: $DEV_MODE" >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then echo "Only one option is supported." >&2; exit 2; fi

DEV_PYTHON="${RWB_DEV_PYTHON:-$HOME/.local/share/rwb-hak-dev/venv/bin/python}"
if [ ! -x "$DEV_PYTHON" ] && [ -z "${RWB_DEV_PYTHON:-}" ]; then
  DEV_PYTHON="$(command -v python3 || true)"
fi
if [ ! -x "$DEV_PYTHON" ]; then
  echo "Python unavailable; set RWB_DEV_PYTHON to a Python 3.10+ venv." >&2
  exit 2
fi

"$DEV_PYTHON" - "$DEV_ROOT" "$DEV_MODE" <<'PY'
import ast
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

root, mode = Path(sys.argv[1]), sys.argv[2]

def fail(message, code=2):
    print(message, file=sys.stderr, flush=True)
    raise SystemExit(code)

def run(args, code=2, timeout=15):
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail(f"Unavailable: {args[0]}: {exc}", code)
    if result.returncode:
        fail((result.stderr or result.stdout or f"{args[0]} failed").strip(), code)
    return result.stdout.strip()

if sys.version_info < (3, 10):
    fail("Python 3.10+ required.")
print(f"Python {sys.version.split()[0]}", flush=True)
try:
    import psycopg2
except ImportError:
    fail("psycopg2 missing. Install requirements-dev.txt in a venv; see docs/dev-environment-20261028.md.")
required = re.search(r"^psycopg2-binary==([^\s]+)$",
                     (root / "requirements-dev.txt").read_text(), re.M).group(1)
if psycopg2.__version__.split()[0] != required:
    fail(f"psycopg2 version differs from requirements-dev.txt ({required}).")
print(f"psycopg2 {required}", flush=True)
for tool, args in (("docker", ["--version"]), ("psql", ["--version"])):
    if not shutil.which(tool):
        fail(f"Missing command: {tool}")
    print(run([tool, *args]), flush=True)
print(run(["docker", "compose", "version"]), flush=True)
config = json.loads(run(["docker", "compose", "config", "--format", "json"]))
service = config["services"]["postgres"]
ports = service.get("ports", [])
if service["image"] != "postgres:16-alpine" or len(ports) != 1:
    fail("Postgres image/port configuration changed; review the dev contract.")
port = ports[0]
if (port.get("host_ip") != "127.0.0.1" or str(port.get("published")) != "5432"
        or int(port.get("target", 0)) != 5432):
    fail("Postgres must be published only on 127.0.0.1:5432.")
print("Compose: PostgreSQL 16, loopback port 5432", flush=True)

# Pinned Olist source d9e49802f3e92d09ee94ab9ccc5e457f207a8959.
# CSV records, not physical lines: review text can contain newlines.
baseline = {
    "olist_orders_dataset.csv": (99441, "8df58ef3d2d7e9944010f7beecd9b75367f5588ec6e3c91cec19ae3345ef9ecf"),
    "olist_order_items_dataset.csv": (112650, "4f6abdbbc94036d0df4a76fa0520c072e31a40119d70f7f370fba1e2285d2bcb"),
    "olist_order_payments_dataset.csv": (103886, "61674868ed7b872aac3dcd95bf774448a88f6426b183f21be55f75af021ffdec"),
    "olist_order_reviews_dataset.csv": (99224, "012b61c7593e34f51fa614efdf802b9c7056ce6aae5307ddb93236e7cfc797d7"),
    "olist_products_dataset.csv": (32951, "3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc"),
    "olist_sellers_dataset.csv": (3095, "31eb9bd50d684526a78f2389413ce61841e97692de7b828fe7d956b534586312"),
    "olist_customers_dataset.csv": (99441, "c26c17f59f3027a6a0dbeb8f1fa373c38f3323ecc84f225a8f4820e5bb288df8"),
    "product_category_name_translation.csv": (71, "a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278"),
}
tree = ast.parse((root / "scripts/load_raw.py").read_text())
mapping = ast.literal_eval(next(node.value for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == "MAPPING" for t in node.targets)))
if {entry[0] for entry in mapping} != set(baseline):
    fail("Loader input list changed; review pinned CSV baseline.")
for filename, table, columns in mapping:
    path = root / "data" / filename
    if not path.is_file():
        fail(f"Missing data/{filename}; do not silently download mutable master.")
    count, expected_hash = baseline[filename]
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
        fail(f"CSV hash changed: {filename}; review source/version before loading.")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        if next(reader) != columns:
            fail(f"CSV header differs from loader: {filename}")
        if sum(1 for _ in reader) != count:
            fail(f"CSV record count changed: {filename}")
    print(f"CSV {filename}: {count} records, SHA-256/header match", flush=True)
if mode == "--offline":
    print("Offline checks passed. Docker daemon and database were not checked.", flush=True)
    raise SystemExit(0)

print("Checking Docker daemon (no startup)...", flush=True)
print("Docker server " + run(["docker", "info", "--format", "{{.ServerVersion}}"], 3), flush=True)
container_name = service.get("container_name", "hack_postgres")
container = json.loads(run(["docker", "inspect", container_name], 3))[0]
labels = container["Config"].get("Labels") or {}
if labels.get("com.docker.compose.project") != config["name"] or labels.get("com.docker.compose.service") != "postgres":
    fail("Container belongs to another Compose project/service; not connecting.", 3)
workdir = labels.get("com.docker.compose.project.working_dir")
if not workdir or Path(workdir).resolve() != root.resolve():
    fail("Container was created from another checkout; inspect ownership before use.", 3)
if not container["State"].get("Running"):
    fail("Project Postgres container is stopped; see guarded startup in runbook.", 3)
print(f"Container {container_name}: running, current checkout owner", flush=True)
environment = service["environment"]
try:
    connection = psycopg2.connect(host="127.0.0.1", port=5432,
        dbname=environment["POSTGRES_DB"], user=environment["POSTGRES_USER"],
        password=environment["POSTGRES_PASSWORD"], connect_timeout=5,
        options="-c default_transaction_read_only=on -c statement_timeout=15000 -c lock_timeout=1500")
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user, current_setting('server_version_num'), current_setting('transaction_read_only')")
        db, user, server, readonly = cursor.fetchone()
        if not 160000 <= int(server) < 170000 or readonly != "on":
            fail("Expected PostgreSQL 16 in a read-only check transaction.", 3)
        print(f"Database {db}, user {user}, server_version_num={server}, read-only={readonly}", flush=True)
        from psycopg2 import sql
        for filename, table, columns in mapping:
            schema, name = table.split(".")
            cursor.execute(sql.SQL("SELECT count(*), count(*) FILTER (WHERE _source_file IS DISTINCT FROM %s) FROM {}.{}").format(
                sql.Identifier(schema), sql.Identifier(name)), (filename,))
            count, wrong_source = cursor.fetchone()
            if count != baseline[filename][0] or wrong_source:
                fail(f"Raw count/source mismatch: {table}: count={count}, wrong_source={wrong_source}", 3)
            print(f"{table}: {count} rows, source-file metadata matches", flush=True)
        cursor.execute("SELECT table_schema, count(*) FROM information_schema.tables WHERE table_schema IN ('core','mart') GROUP BY table_schema ORDER BY table_schema")
        print("Existing core/mart object counts: " + repr(cursor.fetchall()), flush=True)
    connection.rollback()
    connection.close()
except psycopg2.Error as exc:
    fail(f"Database check unavailable: {str(exc).strip()}", 3)
print("Runtime checks passed. Raw counts/metadata checked; full CSV/raw value equality and model correctness are separate checks.", flush=True)
PY
