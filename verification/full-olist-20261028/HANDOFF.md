# Полный Olist: проверка Q1–Q10

- Owner: test sub-agent, Codex / GPT-6.1 Sol.
- UTC start: 2026-10-28T14:01:47Z.
- Checkout: `/Users/a/.t3/worktrees/rwb_hak/t3-a8c97e55`.
- Base: `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`; branch `t3/verify-full-olist`.
- Published input: `aab62d7a59f196be051df12466fb21c0da4659b9`, branch `t3/integrate-q6-q10-marts`.
- Source SQL: `99bcbb366720f912ef6017a40aa5dbd6a671a8a4`.
- Requirements: `558f0f6a38110acc9fcf4386a7e53ece973aedf5`.
- Owned paths: `verification/full-olist-20261028/**`, `scripts/verify-full-olist.py`.
- Status: ready_for_integration_partial; CSV verification complete, full database verification pending.
- UTC update: 2026-10-28T14:13:16.790000+00:00.
- Runner commit: `bc33436` (full SHA is in publication evidence).

## Границы

Общий checkout и index не используются. История категорий и address regression принадлежат другому исполнителю. Разрешены обнаружение проектного validation endpoint, ограниченные SELECT в read-only repeatable-read, CSV oracle и подготовка runner. Нет разрешения на DDL в рабочей БД, перезагрузку raw или тяжёлую полную локальную сборку при guard 78.

## Первые факты

`/Users/a/bin/dev-job preflight` вернул 78: free SSD 26.5 GiB, memory pressure 2, swap 3.72 GiB, heavy_local_allowed=false. Новая полная локальная сборка/fixture не запускается.

`docker ps --format '{{.Names}}\\t{{.Image}}\\t{{.Ports}}'` завершился кодом 1: `Cannot connect to the Docker daemon at unix:///Users/a/.docker/run/docker.sock. Is the docker daemon running?` Docker не запускается и не перезапускается в этой задаче. Discovery другого уже разрешённого проектного endpoint продолжается.


## Выполнено

Полный Olist прочитан потоково из `/Users/a/rwb_hak/data`, без загрузки в БД. Восемь SHA-256, размеры, заголовки и 550 759 строк совпали с `tests/model/input-manifest.lock.json` на `aab62d7`. После вычислений SHA повторно сверены. Исходные CSV не менялись и не скопированы в evidence.

- Независимый CSV oracle Q1–Q10 вычислен дважды. Все агрегаты побайтно совпали; общий output SHA-256: `67f7f5eb34dfc238fcacaa2f1ea921c7eebc0631393c5409e70dcb80a8e6ead4`.
- Q1–Q5: 18 контрольных значений прошли, включая пустой ноябрь 2016, revenue `13221498.11`, чек `159.88`, payment comparator `159.86`, покупателей `96096`, повторных `2997`, window-вариант, 74 категории и лидеров продавцов/категорий. Это значения CSV oracle, не ответы из core.
- Q6–Q10: девять сравнений с опубликованными CSV oracles, все PASS. Сверялись все строки и знаменатели: Q6 153 day/price rows, Q7 68 rows (17 штатов × 2 популяции × 2 late basis), Q8 8 статусов, Q9 27 штатов и 10 method/period rows, Q10 40 variant rows и 2 coverage rows. Обе delivered score policies дополнительно сверены со вторым review oracle.
- Для всех 11 dimensions/facts рассчитаны ожидаемые business-column multiset fingerprints из CSV. Их колонки статически совпали с DDL на `aab62d7`. Это **ожидания для сверки**, не равенство с живым core.
- Четыре малые offline-проверки runner прошли: PostgreSQL CSV NULL/quoted-empty/multiline semantics, multiplicity/value mutation detection, неверный знаменатель и NULL→0, отбрасывание DDL/psql-команд.
- На собственном временном PostgreSQL **16.15**, `shared_buffers=16MB`, выполнена только трёхстрочная synthetic SELECT проверка транспорта/хеширования. Named cursor и сравнение fingerprints прошли; `REPEATABLE READ READ ONLY` подтверждён; запись отвергнута SQLSTATE `25006`. Сервер остановлен, runtime удалён. Это не повтор модельных fixtures другого исполнителя и не Olist DB PASS.

[Основной summary](db-run-02/summary.json), [все CSV агрегаты](db-run-02/csv-oracle.json), [первый CSV запуск](csv-run-01/summary.json), [driver evidence](pg16-readonly-driver/summary.json), [unit checks](runner-tests.json). Снимок фактически использованного runner сохранён и проверен SHA в каждом каталоге запуска.

## Проверенный blocker полного DB-прогона

[Discovery](discovery.json) сохраняет команды, время, exit codes и точные ошибки. Источник endpoint — опубликованный `docs/dev-environment-20261028.md:51` и `AGENTS.md`:

```text
127.0.0.1:5432 / marketplace / hack
psql: error: connection to server at "127.0.0.1", port 5432 failed: Connection refused
        Is the server running on that host and accepting TCP/IP connections?
```

Docker daemon также недоступен; listener на 5432 не найден. `RWB_VALIDATION_DSN`, `RWB_TEST_DSN`, `PGSERVICE`, `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` не заданы. Другого действующего согласованного validation endpoint в опубликованных runbooks/evidence не найдено. Произвольные VM и production не проверялись.

Две проверки guard дали 78; последняя: free SSD 26.43 GiB, memory pressure 2, swap 3.68 GiB. Новая полная локальная сборка/fixture запрещена. Docker не запускался, лимиты не менялись, уменьшенные buffers не использовались для обхода guard с полным Olist.

`db-run-02` действительно запущен в режиме `db-readonly` после полного CSV oracle; завершился **exit 3** (`csv_pass_db_unavailable_or_identity_only`, database status `unavailable`). Соединение не установлено. Версия/имя БД/схемы/содержимое/SELECT grants проектного endpoint не подтверждены. Никаких SQL SELECT по полному core он не выполнил.

| Проверка | Состояние |
|---|---|
| Full pinned CSV Q1–Q10 oracle + published-oracle equality | PASS |
| Full SELECT из `99bcbb3` на существующем core | NOT RUN: endpoint unavailable |
| CSV→raw и CSV→core value/multiplicity binding | NOT RUN; ожидаемые fingerprints готовы |
| Integrated mart SELECT на `aab62d7` | NOT RUN |
| Full atomic clean build / rebuild equality / late failure rollback / raw unchanged | NOT RUN; guard 78 + no validation DB |
| История категорий + address regression после integration | Не входят в этот PASS; отдельный обязательный rerun |

## Runner и команды продолжения

[`scripts/verify-full-olist.py`](../../scripts/verify-full-olist.py) читает только pinned Git blobs и CSV. Он не меняет index, не запускает сервисы, не скачивает данные, не устанавливает зависимости, не строит модель и не создаёт таблицы/views, даже временные. В DB-режиме подключается к явно выбранному уже обнаруженному локальному проектному endpoint; пароль использует из существующей libpq конфигурации вне Git. Не передавать URI/пароль в CLI или evidence.

Для нового checkout сначала получить обе опубликованные зависимости (достаточно одного раза):

```sh
git fetch origin refs/heads/t3/integrate-q6-q10-marts:refs/remotes/origin/t3/integrate-q6-q10-marts refs/heads/t3/implement-q6-q10-answers:refs/remotes/origin/t3/implement-q6-q10-answers
```

В каталоге с этим patch, Python 3.11+:

```sh
python3 scripts/verify-full-olist.py --data-dir /Users/a/rwb_hak/data --output-dir verification/full-olist-20261028/next-csv --mode csv
PYTHONDONTWRITEBYTECODE=1 python3 verification/full-olist-20261028/test_runner.py
```

После появления уже согласованного действующего полного endpoint (без DDL и без нового full fixture) выполнить:

```sh
python3 scripts/verify-full-olist.py --data-dir /Users/a/rwb_hak/data --output-dir verification/full-olist-20261028/next-db --mode db-readonly --existing-project-endpoint --host 127.0.0.1 --port 5432 --database marketplace --user hack
```

DB-режим требует уже имеющийся `psycopg` 3; в текущем Python он есть. Он проверяет PG16/database/schema identity и SELECT rights, фиксирует snapshot и hashes фактических mart view definitions, сравнивает все business columns raw/core с CSV и исполняет точные SELECT/CTE исходников `99bcbb3`. Q1–Q5 читаются через опубликованные mart views. Затем отдельной проверкой выполняются integrated SELECTs на `aab62d7`; отсутствие новых views не маскируется под integrated PASS. Все этапы идут в одном `REPEATABLE READ READ ONLY`, `statement_timeout=20s`, `lock_timeout=2s`, `work_mem=4MB`, без parallel gather. Слишком медленный запрос должен завершиться timeout; лимиты не повышать молча.

В бизнес-агрегатах применяется absolute numeric tolerance `1E-12` для дробных PG средних; counts/NULL/строки/ключи проверяются точно с учётом этой numeric ветки. Raw/core сравнение — count + SHA-256 multiset каждой канонической строки, с повторениями и NULL/empty distinction. Это криптографическая сверка содержимого при стандартном предположении отсутствия коллизий SHA-256, не двунаправленный EXCEPT ALL. Нельзя подменять ею lifecycle или утверждать происхождение старого core только по совпадению итоговых сумм. Хеши view definitions фиксируют реально прочитанный код, но не восстанавливают SHA неизвестной старой сборки.

Полный atomic lifecycle: существующий `tests/model/validate-lifecycle.sh` на `aab62d7` уже содержит clean build, rebuild/fingerprint equality, намеренную позднюю ошибку/rollback, raw unchanged и controls. Сейчас он **не запускался**. Он требует отдельную уже подготовленную validation DB с raw и пустыми core/mart, останавливает запуск для marketplace и использует temp DDL для raw comparison. Поэтому на рабочем endpoint для нынешней read-only задачи он непригоден. Будущий полный запуск допустим только после успешного guard и подготовки соответствующего проектного validation endpoint; не создавать полный local fixture при 78. Запуск владельцем такого стенда из checkout с полным pinned input:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host bash tests/model/validate-lifecycle.sh
```

На всём lifecycle должны быть реально остановлены raw/model writers, а libpq должен явно указывать на dedicated validation DB, а не marketplace. Сам runner raw не загружает и не удаляет. Его вывод и input/code hashes нужно сохранить в отдельный evidence-каталог, затем выполнить наш `db-readonly` на той же БД. Наличие этой команды не является выполнением полного lifecycle.

## Публикация и зависимости

Выполнен read-only `git fetch` main и integration refs, без pull/reset/merge. Проверено, что используется отдельный worktree index `/Users/a/rwb_hak/.git/worktrees/t3-a8c97e55/index`; общий dirty checkout не менялся. Изменения строго в OWNED paths; общий registry, app, dashboard и `model/**` не редактировались. Подагенты не запускались.

[Проверка target tree](target-tree.json): integration ref = `aab62d7a59f196be051df12466fb21c0da4659b9`. Свежий main = `6452806eae21d13126da9de8ebaba01a2152eaea`, предыдущий `bbbfab8` уже не текущий. Main пока не содержит `model/55_answers_block_b.sql` и трёх опубликованных experiment-oracles. Это зависимость интеграции, а не удаление этими правками. Ветка test-пакета основана на `2f0a8de`; переносить только два её OWNED commits в integration target, не заменять target tree состоянием этой старой базы. Сам runner читает закреплённые blobs через Git, поэтому проверяет `aab62d7`, даже находясь в старом checkout.

Семантика и named variants сохранены; PASS не означает human approval новых метрик. После объединения истории категорий другой исполнитель должен повторно проверить адреса/категории и затронутые Q1–Q10 на новом SHA. Наши expectations описывают 11 таблиц старого `aab62d7`; дополнительные колонки/history tables требуют адресного расширения mapping и нового evidence. Старые CSV/driver результаты не объявлять проверкой интегрированной истории.
