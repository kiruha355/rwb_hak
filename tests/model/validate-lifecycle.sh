#!/usr/bin/env bash
# Prepared full DB acceptance protocol. Not run on the guard-blocked Mac.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd -- "$repo_root"
[[ ${RWB_RAW_RELOAD_PAUSED:-} == 1 ]] || { printf '%s\n' 'Pause all raw writers and set RWB_RAW_RELOAD_PAUSED=1 first.' >&2; exit 2; }
[[ ${RWB_DB_MODE:-host} == host ]] || { printf '%s\n' 'Lifecycle protocol uses host psql/libpq against an existing dedicated validation DB.' >&2; exit 2; }
command -v psql >/dev/null || { printf '%s\n' 'psql unavailable; DB execution pending.' >&2; exit 2; }
if [[ -z ${PGSERVICE:-} ]]; then
    export PGHOST=${PGHOST:-127.0.0.1} PGPORT=${PGPORT:-5432}
    export PGDATABASE=${PGDATABASE:-marketplace} PGUSER=${PGUSER:-hack}
fi
export PGCONNECT_TIMEOUT=${PGCONNECT_TIMEOUT:-5}
# psycopg2 and psql must resolve the SAME libpq environment/service, rather than
# accidentally comparing CSV/raw in a different DSN from the lifecycle build.
export RWB_VALIDATION_DSN='application_name=capibara_validation'
psql_cmd=(psql -X -w -v ON_ERROR_STOP=1 -P pager=off)
db_name=$("${psql_cmd[@]}" -Atc 'SELECT current_database()')
case "$db_name" in marketplace|postgres|template0|template1|'') printf '%s\n' 'Use a dedicated validation DB, never the working marketplace DB.' >&2; exit 2;; esac
object_count=$("${psql_cmd[@]}" -Atc "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('core','mart') AND c.relkind IN ('r','v','m','p')")
[[ "$object_count" == 0 ]] || { printf '%s\n' 'Clean-build acceptance requires empty core/mart on the dedicated DB.' >&2; exit 2; }
evidence_dir=$(mktemp -d "${TMPDIR:-/tmp}/capibara-validation.XXXXXXXX")
printf 'Evidence directory: %s\n' "$evidence_dir"
python3 scripts/input-manifest.py --verify-pinned --output "$evidence_dir/input.json"
# No credentials are copied into evidence; libpq uses the environment/service.
python3 scripts/verify-model.py --raw-inputs > "$evidence_dir/csv-raw.json"
"${psql_cmd[@]}" -qAt -F $'\t' -f tests/model/fingerprint.sql > "$evidence_dir/raw-before.tsv"
bash scripts/build-model.sh build > "$evidence_dir/clean-build.log" 2>&1
"${psql_cmd[@]}" -qAt -F $'\t' -f tests/model/fingerprint.sql > "$evidence_dir/first.tsv"
bash scripts/build-model.sh build > "$evidence_dir/rebuild.log" 2>&1
"${psql_cmd[@]}" -qAt -F $'\t' -f tests/model/fingerprint.sql > "$evidence_dir/second.tsv"
diff -u "$evidence_dir/first.tsv" "$evidence_dir/second.tsv"
status=0
"${psql_cmd[@]}" -1 -f tests/model/rollback.sql > "$evidence_dir/injected-failure.log" 2>&1 || status=$?
[[ "$status" == 3 ]] || { printf 'Expected psql script-error exit 3; got %s. Inspect connection/transaction outcome.\n' "$status" >&2; exit 1; }
python3 - "$evidence_dir/injected-failure.log" <<'PY'
from pathlib import Path
import sys
if 'W11_INJECTED_LATE_FAILURE_AFTER_ALL_CHECKS' not in Path(sys.argv[1]).read_text():
    raise SystemExit('Expected late failure was not reached; a different failure is not acceptance')
PY
"${psql_cmd[@]}" -qAt -F $'\t' -f tests/model/fingerprint.sql > "$evidence_dir/after-rollback.tsv"
diff -u "$evidence_dir/second.tsv" "$evidence_dir/after-rollback.tsv"
python3 - "$evidence_dir" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
def raw(path): return [line for line in path.read_text().splitlines() if line.startswith('raw.')]
if not raw(p/'raw-before.tsv') or raw(p/'raw-before.tsv') != raw(p/'after-rollback.tsv'):
    raise SystemExit('Raw fingerprints missing or changed')
PY
bash scripts/build-model.sh check > "$evidence_dir/check.log" 2>&1
bash scripts/build-model.sh control > "$evidence_dir/control.log" 2>&1
python3 scripts/input-manifest.py --verify-pinned --compare "$evidence_dir/input.json" --output "$evidence_dir/input-after.json"
printf 'Lifecycle checks passed on dedicated DB %s; evidence %s\n' "$db_name" "$evidence_dir"
