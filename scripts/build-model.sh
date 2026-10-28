#!/usr/bin/env bash
# Read existing raw only. No service startup, setup.sh, download or raw loader.
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"
mode=${1:-build}
if [[ $# -gt 1 ]]; then
    printf 'Usage: bash scripts/build-model.sh [build|check|control|answers|rebuild-check]\n' >&2
    exit 2
fi
case "$mode" in
    build|check|control|answers|rebuild-check) ;;
    *) printf 'Unknown model command: %s\n' "$mode" >&2; exit 2 ;;
esac

# This is an operator assertion, not an automatic detection of concurrent reload.
# Advisory locking below only serializes cooperating model clients. The existing
# loader does not take that lock, so it must be stopped for this entire command.
if [[ ${RWB_RAW_RELOAD_PAUSED:-} != 1 ]]; then
    printf '%s\n' 'Refusing model access: first pause ALL raw reload/DDL writers for the whole command.' 'Then set RWB_RAW_RELOAD_PAUSED=1. See docs/build-runbook.md; REPEATABLE READ alone is insufficient.' >&2
    exit 2
fi

db_mode=${RWB_DB_MODE:-host}
case "$db_mode" in
    host)
        command -v psql >/dev/null || { printf 'psql is required on PATH.\n' >&2; exit 2; }
        # Respect an explicitly configured libpq service. Never print credentials.
        if [[ -z ${PGSERVICE:-} ]]; then
            export PGHOST=${PGHOST:-127.0.0.1} PGPORT=${PGPORT:-5432}
            export PGDATABASE=${PGDATABASE:-marketplace} PGUSER=${PGUSER:-hack}
        fi
        export PGCONNECT_TIMEOUT=${PGCONNECT_TIMEOUT:-5}
        psql_cmd=(psql)
        ;;
    docker)
        command -v docker >/dev/null || { printf 'Docker CLI is required. No daemon will be started.\n' >&2; exit 2; }
        psql_cmd=(docker compose -f "$repo_root/docker-compose.yml" exec -T "${RWB_DB_SERVICE:-postgres}" psql -U "${PGUSER:-hack}" -d "${PGDATABASE:-marketplace}")
        ;;
    *) printf 'RWB_DB_MODE must be host or docker.\n' >&2; exit 2 ;;
esac
command -v python3 >/dev/null || { printf 'python3 is required to resolve SQL includes.\n' >&2; exit 2; }

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/capibara-build.XXXXXXXX")
trap 'rm -rf -- "$work_dir"' EXIT

# Resolve \ir locally, before connecting. Docker does not mount model/; expanded
# SQL streams through stdin, without copying code/secrets into the container.
# Also catches missing stage files BEFORE any model SQL is executed.
render_sql() {
    python3 - "$repo_root" "$@" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
def emit(path, stack=()):
    path = path.resolve()
    if not path.is_relative_to(root) or path in stack:
        raise ValueError(f"Unsafe or cyclic SQL include: {path}")
    content = path.read_text(encoding="utf-8")
    print(r"\echo [capibara] " + str(path.relative_to(root)))
    for line in content.splitlines():
        match = re.fullmatch(r"\s*\\ir\s+([A-Za-z0-9_./-]+)\s*", line)
        if match:
            emit(path.parent / match[1], (*stack, path))
        elif re.match(r"\s*\\i(?:r)?(?:\s|$)", line):
            raise ValueError(f"Unsupported SQL include in {path}: {line}")
        else:
            print(line)
try:
    for filename in sys.argv[2:]:
        emit(root / filename)
except (OSError, ValueError) as error:
    print(f"SQL preflight failed: {error}", file=sys.stderr)
    raise SystemExit(2)
PY
}

write_preamble() {
    cat <<'SQL'
\set ON_ERROR_STOP on
\set VERBOSITY verbose
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '10min';
SET LOCAL idle_in_transaction_session_timeout = '1min';
SET LOCAL search_path = pg_catalog, pg_temp;
SET LOCAL DateStyle = 'ISO, YMD';
SET LOCAL TimeZone = 'UTC';
SET LOCAL capibara.raw_reload_paused = '1';
\if :{?report_release}
SELECT set_config('capibara.report_release', :'report_release', true);
\endif
DO $guard$
BEGIN
    IF current_setting('server_version_num')::integer < 160000 THEN
        RAISE EXCEPTION 'PostgreSQL 16 or newer is required';
    END IF;
    IF NOT pg_try_advisory_xact_lock(1667330674, 1) THEN
        RAISE EXCEPTION 'Another cooperating Capibara model command is active';
    END IF;
END
$guard$;
SQL
}

run_prepared() {
    local sql_file=$1
    shift
    local status=0
    "${psql_cmd[@]}" -X -1 -v ON_ERROR_STOP=1 -w -P pager=off -v "report_release=${RWB_REPORT_RELEASE:-}" "$@" -f - < "$sql_file" || status=$?
    if (( status != 0 )); then
        printf '%s\n' "Model command failed (psql exit $status). See the SQL error above." 'No automatic retry or raw reload was performed. A server SQL error aborts the transaction; after a lost connection inspect commit outcome before retrying.' >&2
    fi
    return "$status"
}

prepare_entry() {
    local output=$1
    shift
    write_preamble > "$output"
    render_sql "$@" >> "$output"
}

build_once() {
    prepare_entry "$work_dir/build.sql" model/build.sql
    run_prepared "$work_dir/build.sql"
}

fingerprint() {
    local output=$1
    write_preamble > "$work_dir/fingerprint.sql"
    cat >> "$work_dir/fingerprint.sql" <<'SQL'
-- A content comparison, not a CSV/raw equality proof. Exclude only the check
-- execution timestamp; every other model value and duplicate row contributes.
SELECT format(
    'SELECT %L, count(*), encode(sha256(convert_to(coalesce(string_agg(row_hash, %L ORDER BY row_hash), %L), %L)), %L) FROM (SELECT encode(sha256(convert_to((to_jsonb(t) %s)::text, %L)), %L) AS row_hash FROM %I.%I AS t) AS rows',
    n.nspname || '.' || c.relname, '', '', 'UTF8', 'hex',
    CASE WHEN n.nspname = 'core' AND c.relname = 'check_results' THEN '- ''checked_at''' ELSE '' END,
    'UTF8', 'hex', n.nspname, c.relname)
FROM pg_class AS c JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE n.nspname IN ('core', 'mart') AND c.relkind IN ('r', 'v', 'm', 'p')
ORDER BY n.nspname, c.relname
\gexec
SQL
    run_prepared "$work_dir/fingerprint.sql" -q -A -t -F $'\t' > "$output"
}

case "$mode" in
    build) build_once ;;
    check)
        prepare_entry "$work_dir/check.sql" model/05_typecheck.sql model/90_checks.sql
        run_prepared "$work_dir/check.sql"
        ;;
    control)
        if [[ ! ${RWB_VERIFIED_INPUT_MANIFEST_SHA256:-} =~ ^[0-9a-f]{64}$ ]]; then
            printf '%s\n' 'Pinned controls require RWB_VERIFIED_INPUT_MANIFEST_SHA256 (64 lowercase hex characters).' 'First establish live raw/input equality and core invariants on this same paused generation. Hashing a local manifest alone is insufficient.' >&2
            exit 2
        fi
        prepare_entry "$work_dir/control.sql" answers/control.sql
        run_prepared "$work_dir/control.sql" -v "verified_input_manifest_sha256=$RWB_VERIFIED_INPUT_MANIFEST_SHA256"
        ;;
    answers)
        shopt -s nullglob
        answer_files=(answers/q[0-9][0-9]*.sql)
        if (( ${#answer_files[@]} == 0 )); then
            printf 'No answers/qNN.sql files exist yet.\n' >&2
            exit 2
        fi
        answer_files+=(answers/q06-q10/q06.sql answers/q06-q10/q07.sql
            answers/q06-q10/q08.sql answers/q06-q10/q09.sql
            answers/q06-q10/q10.sql answers/q06-q10/q10_coverage.sql)
        for supplement in answers/payment_reconciliation.sql answers/review_weights.sql; do
            [[ ! -f $supplement ]] || answer_files+=("$supplement")
        done
        prepare_entry "$work_dir/answers.sql" "${answer_files[@]}"
        run_prepared "$work_dir/answers.sql"
        ;;
    rebuild-check)
        build_once
        fingerprint "$work_dir/first.tsv"
        build_once
        fingerprint "$work_dir/second.tsv"
        if ! diff -u "$work_dir/first.tsv" "$work_dir/second.tsv"; then
            printf 'Repeated build changed model content. Both builds committed; inspect the diff above.\n' >&2
            exit 1
        fi
        printf 'Repeated build fingerprints match (check_results.checked_at excluded).\n'
        ;;
esac
