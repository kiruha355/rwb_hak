# W11 PostgreSQL 16 tiny smoke: passed

UTC: 2026-10-28T09:57:18.471172+00:00 → 2026-10-28T09:57:20.446111+00:00; elapsed 1.975227 s.

Only the 16 repository synthetic cases were requested; no real Olist fixture or full build.

PostgreSQL: `postgres (PostgreSQL) 16.15 (Homebrew)`.
Runtime/cluster preserved: `/Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028`.
Source hashes unchanged: `True`.

Summary: `{"executed": 16, "positive_passed": 4, "expected_failures_detected": 12, "unexpected_failures": 0, "not_run": 0}`.
Cleanup: `{"stop_exit_code": 0, "cluster_preserved": true, "database_deleted": false, "runtime_deleted": false, "status_exit_code": 3, "postmaster_pid_file_absent": true, "unix_socket_absent": true, "owned_postmaster_absent": true}`.

| Case | Actual result | SQLSTATE / stage |
|---|---|---|
| baseline_fanout_null_zero_late | passed |   |
| fractional_scale_preserved | passed |   |
| nan_rejected_before_cast | expected_failure_detected | P0001 05_typecheck.sql |
| invalid_integer_key | expected_failure_detected | P0001 05_typecheck.sql |
| null_mandatory_key | expected_failure_detected | P0001 05_typecheck.sql |
| duplicate_item_key | expected_failure_detected | 23505 20_facts.sql |
| dangling_product_fk | expected_failure_detected | 23503 20_facts.sql |
| new_status_retained_warning | passed |   |
| review_payload_conflict_retained_warning | passed |   |
| duplicate_review_pair | expected_failure_detected | 23505 20_facts.sql |
| calendar_gap_detected | expected_failure_detected | 23514 rerun invariant checks |
| compensating_order_errors_detected | expected_failure_detected | 23514 rerun invariant checks |
| lost_review_text_detected | expected_failure_detected | 23514 rerun invariant checks |
| missing_child_detected | expected_failure_detected | 23514 rerun invariant checks |
| replaced_child_key_detected | expected_failure_detected | 23514 rerun invariant checks |
| duplicate_core_multiplicity_detected | expected_failure_detected | 23514 rerun invariant checks |

## Footprint and evidence

49 native business rows in eight test inputs; 730 generated calendar days. Each case is isolated by a savepoint.
Cluster sizes: `{"after_initdb": {"apparent_bytes": 40373873, "files": 968, "allocated_kib": 39472}, "after_fixtures_before_stop": {"apparent_bytes": 69666604, "files": 2106, "allocated_kib": 68100}, "after_stop_preserved": {"apparent_bytes": 69762138, "files": 1272, "allocated_kib": 68192}}`.
No dependency install; existing approved venv provides psycopg2 2.9.13.
The system Python lacked psycopg2; using the documented existing venv resolved this without writes to it.
Requested max_connections=5, shared_buffers=8MB, work_mem=1MB, maintenance_work_mem=8MB; autovacuum/jit/parallel workers off.
listen_addresses is empty; socket directory/socket permissions are 0700; TCP-listener absence checked for the owned postmaster.
Full command stdout/stderr, source SHA256 and effective settings: `/Users/a/rwb_hak/research/implementation-review-20261028/pg-smoke.json`.
Verbose PostgreSQL error log: `/Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/server.log`.

## Commands actually executed

```sh
git rev-parse HEAD  # exit=0
git rev-parse origin/main  # exit=0
/opt/homebrew/opt/postgresql@16/bin/postgres --version  # exit=0
/Users/a/.local/share/rwb-hak-dev/venv/bin/python3 -c 'import sys,psycopg2; print(sys.version); print(psycopg2.__version__)'  # exit=0
/Users/a/.local/share/rwb-hak-dev/venv/bin/python3 scripts/verify-model.py --plan  # exit=0
/opt/homebrew/opt/postgresql@16/bin/initdb -D /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/data --username a --encoding=UTF8 --locale=C --auth-local=peer --auth-host=reject --no-clean --set=max_connections=5 --set=shared_buffers=8MB --set=work_mem=1MB --set=maintenance_work_mem=8MB --set=autovacuum=off --set=jit=off --set=max_worker_processes=0 --set=max_parallel_workers=0 --set=max_parallel_workers_per_gather=0 --set=max_parallel_maintenance_workers=0 --set=wal_buffers=512kB --set=min_wal_size=32MB --set=max_wal_size=64MB  # exit=0
/usr/bin/du -sk /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/data  # exit=0
/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/data -l /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/server.log -w -t 15 start  # exit=0
/usr/sbin/lsof -nP -a -p 94341 -iTCP -sTCP:LISTEN  # exit=1
/opt/homebrew/opt/postgresql@16/bin/psql -X -w -v ON_ERROR_STOP=1 -A -t -h /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/socket -p 55416 -U a -d postgres -c 'CREATE DATABASE rwb_w11_pg16_smoke'  # exit=0
/opt/homebrew/opt/postgresql@16/bin/psql -X -w -v ON_ERROR_STOP=1 -A -t -h /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/socket -p 55416 -U a -d rwb_w11_pg16_smoke -c 'SELECT json_build_object('"'"'version'"'"',version(),'"'"'server_version_num'"'"',current_setting('"'"'server_version_num'"'"'),'"'"'database'"'"',current_database(),'"'"'user'"'"',current_user,'"'"'data_directory'"'"',current_setting('"'"'data_directory'"'"'),'"'"'inet_server_addr'"'"',inet_server_addr())'  # exit=0
/opt/homebrew/opt/postgresql@16/bin/psql -X -w -v ON_ERROR_STOP=1 -A -t -h /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/socket -p 55416 -U a -d rwb_w11_pg16_smoke -c 'SELECT json_object_agg(name,json_build_object('"'"'setting'"'"',setting,'"'"'unit'"'"',unit)) FROM pg_settings WHERE name IN ('"'"'listen_addresses'"'"','"'"'unix_socket_directories'"'"','"'"'unix_socket_permissions'"'"','"'"'max_connections'"'"','"'"'shared_buffers'"'"','"'"'work_mem'"'"','"'"'maintenance_work_mem'"'"','"'"'autovacuum'"'"','"'"'jit'"'"','"'"'max_worker_processes'"'"','"'"'max_parallel_workers'"'"','"'"'max_parallel_workers_per_gather'"'"','"'"'max_parallel_maintenance_workers'"'"','"'"'wal_buffers'"'"','"'"'min_wal_size'"'"','"'"'max_wal_size'"'"')'  # exit=0
/opt/homebrew/opt/postgresql@16/bin/psql -X -w -v ON_ERROR_STOP=1 -A -t -h /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/socket -p 55416 -U a -d rwb_w11_pg16_smoke -c 'SELECT count(*) FROM pg_namespace WHERE nspname IN ('"'"'raw'"'"','"'"'core'"'"','"'"'mart'"'"') OR nspname LIKE '"'"'w11\_%'"'"' ESCAPE '"'"'\'"'"''  # exit=0
/bin/ps -p 94341 -o pid=,ppid=,rss=,comm=  # exit=0
/Users/a/.local/share/rwb-hak-dev/venv/bin/python3 scripts/verify-model.py --run-fixtures  # exit=0
/opt/homebrew/opt/postgresql@16/bin/psql -X -w -v ON_ERROR_STOP=1 -A -t -h /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/socket -p 55416 -U a -d rwb_w11_pg16_smoke -c 'SELECT count(*) FROM pg_namespace WHERE nspname IN ('"'"'raw'"'"','"'"'core'"'"','"'"'mart'"'"') OR nspname LIKE '"'"'w11\_%'"'"' ESCAPE '"'"'\'"'"''  # exit=0
/usr/bin/du -sk /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/data  # exit=0
/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/data -m fast -w -t 15 stop  # exit=0
/opt/homebrew/opt/postgresql@16/bin/pg_ctl -D /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/data status  # exit=3
/bin/ps -p 94341 -o pid=,ppid=,rss=,comm=  # exit=1
/usr/bin/du -sk /Users/a/.local/share/rwb-hak-dev/pg16-smoke-20261028/data  # exit=0
```

RWB_TEST_DSN was set only in the task child environment to this Unix socket/database; no DSN/password value is recorded.

## Boundaries

- Synthetic PG16 pass does not establish a real Olist core/mart build.
- No pinned CSV/raw binding or real Olist control answers were run.
- No build.sql orchestration, lifecycle/rebuild/late rollback, loader races, permissions matrix or benchmark were tested.
- Only this task-owned PostgreSQL may be stopped; cluster/database contents are preserved.
- No SQL, shared scripts/docs/registries, git index, commits or pushes are modified.

## Measurement precision

The exact fixture CLI ran for 0.944424 s; init/start/check/stop total 1.975227 s. Preserved cluster occupies 66.59 MiB allocated.

17 source files were hashed before and after; all hashes stayed equal. The runner independently reported the same seven stage hashes. No test/live raw/core/mart schemas remain after rollback.

initdb --set overrides were supplied, but its captured default-detection banner still says max_connections 100 and shared_buffers 128MB. No long-running server was started with those defaults; effective own server settings were independently verified as 5 and 8MB. Transient initdb probe memory was not measured.

The recorded 13,520 KiB RSS is an idle postmaster snapshot only, not combined cluster memory or peak RSS. The 128 MiB pre-run estimate is not a measured or enforced ceiling.
