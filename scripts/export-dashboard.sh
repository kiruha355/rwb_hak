#!/usr/bin/env bash
# Export core/mart into dashboard/data.js for the static HTML dashboard.
# Read-only transaction; same connection modes as scripts/build-model.sh.
set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$repo_root"

case "${RWB_DB_MODE:-host}" in
    host)
        command -v psql >/dev/null || { printf 'psql is required on PATH.\n' >&2; exit 2; }
        if [[ -z ${PGSERVICE:-} ]]; then
            export PGHOST=${PGHOST:-127.0.0.1} PGPORT=${PGPORT:-5432}
            export PGDATABASE=${PGDATABASE:-marketplace} PGUSER=${PGUSER:-hack}
        fi
        psql_cmd=(psql -w)
        ;;
    docker)
        psql_cmd=(docker compose -f "$repo_root/docker-compose.yml" exec -T "${RWB_DB_SERVICE:-postgres}" psql -U "${PGUSER:-hack}" -d "${PGDATABASE:-marketplace}")
        ;;
    *) printf 'RWB_DB_MODE must be host or docker.\n' >&2; exit 2 ;;
esac

out=dashboard/data.js
tmp=$(mktemp "${TMPDIR:-/tmp}/capibara-dashboard.XXXXXXXX")
trap 'rm -f -- "$tmp"' EXIT
"${psql_cmd[@]}" -X -q -1 -At -v ON_ERROR_STOP=1 < dashboard/export.sql > "$tmp"
# Re-serialize without the spaces PostgreSQL puts into json output (~25% of size).
python3 - "$tmp" "$out" <<'PY'
import json, sys
prefix = 'window.CAPIBARA_DATA = '
text = open(sys.argv[1], encoding='utf-8').read().strip()
if not text.startswith(prefix) or not text.endswith(';'):
    raise SystemExit('Export produced no data document.')
data = json.loads(text[len(prefix):-1])
n = data['orders']['n']
assert len(data['orders']['id']) == 32 * n, 'order ids are not 32 chars each'
for key, value in data['orders'].items():
    assert key == 'n' or len(value) == (32 * n if key == 'id' else n), key
with open(sys.argv[2], 'w', encoding='utf-8') as f:
    f.write(prefix + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
PY
trap - EXIT
chmod 644 "$out"
printf '[capibara] %s: %s bytes\n' "$out" "$(wc -c < "$out" | tr -d ' ')"
