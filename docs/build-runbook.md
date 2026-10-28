# Сборка core и mart из существующего raw

W-09 · repository `kiruha355/rwb_hak` · input main
`1939068295d7203a15cbb0a1ab5d407caca90f58` · PostgreSQL 16.
Контракт: [model/CONTRACT.md](../model/CONTRACT.md). Реализация подготовлена ИИ;
SQL execution, повторная сборка, rollback и проверки конкурентности **pending**.
Локальный guard вернул 78; Docker daemon отсутствует. Этот пакет не запускает
Docker, VM, установки, loader или временный сервер и не обходит guard.

## Одна команда

Сначала выполнить протокол остановленной загрузки ниже. В каталоге репозитория:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host make build
```

Это подключается **к уже работающей БД** через локальный `psql`. Без `PGSERVICE`
defaults: `PGHOST=127.0.0.1`, `PGPORT=5432`, `PGDATABASE=marketplace`, `PGUSER=hack`.
Их можно переопределить переменными libpq. Для иного стенда явно задать endpoint
или настроенный вне Git сервис; не полагаться на defaults при работе с чужой БД:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host PGSERVICE=capibara make build
```

Пароль хранить в пользовательском `.pgpass` с правами 0600 либо в разрешённом
хранилище libpq. Wrapper использует `-w`: он не зависает на password prompt.
Не сохранять пароль/URI с credentials в Makefile, SQL, shell history или evidence.
Учебный endpoint и безопасная подготовка собственного контейнера описаны в
[dev-environment-20261028.md](dev-environment-20261028.md). `setup.sh` не является
частью сборки модели: он загружает и очищает raw.

Альтернатива без host `psql`, только для уже запущенного Compose PostgreSQL:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=docker make build
```

Используется `docker compose -f docker-compose.yml exec -T postgres psql -U hack
-d marketplace`. `RWB_DB_SERVICE` меняет service; `PGUSER`/`PGDATABASE` — user/db.
Соединение внутри контейнера идёт через его Unix socket; host `PGHOST`/`PGSERVICE`
туда не переносятся. Если нужна password authentication, настройка libpq должна
существовать внутри контейнера; wrapper не копирует auth-файлы. SQL/includes
разворачиваются локально и передаются через stdin: `model/` монтировать или
копировать в контейнер не нужно. Ни `up`, ни `start`, ни `restart` не вызываются.

## Команды и доказательства

| Команда | Что выполняет | Чего результат не доказывает |
|---|---|---|
| `make build` | `00 → 05 → 10 → 20 → 30 → 40 → 50 → 90` в одной транзакции | Нужны фактический PG run и stderr, а не наличие файлов |
| `make check` | `05_typecheck.sql` и `90_checks.sql` в одной транзакции; обновляет `core.check_results` | Это не read-only команда и не pinned business regression |
| `make control` | [answers/control.sql](../answers/control.sql), отдельно от инвариантов build | Контрольные числа действуют только для соответствующего baseline |
| `make answers` | Найденные `answers/qNN*.sql` по порядку номера, затем money/review variants | Отсутствующие Q6–Q10 не становятся выполненными |
| `make manifest` | `python3 scripts/input-manifest.py --data-dir data --verify-pinned` | CSV hashes/header/count не доказывают равенство загруженного raw |
| `make rebuild-check` | Две полные сборки и сравнение content fingerprints всех relations core/mart между ними | Не тестирует rollback, конкурентность или CSV↔raw equality |

Для всех DB-команд требуется `RWB_RAW_RELOAD_PAUSED=1`. `make manifest` не
подключается к БД и не требует этой переменной. Для сохранения отдельного input
manifest используйте CLI владельца W-11:

```sh
python3 scripts/input-manifest.py --data-dir data --verify-pinned --output /tmp/capibara-input-manifest.json
python3 scripts/input-manifest.py --data-dir data --verify-pinned --compare /tmp/capibara-input-manifest.json
```

Build включает только относительные инварианты, не известные бизнес-числа.
`90_checks.sql` создаёт/обновляет `core.run_checks()` и вызывает её; исключение
содержит имена и детали упавших проверок. Нельзя выдавать старую committed
`core.check_results` после failed build за журнал новой попытки.

`make control` дополнительно требует `RWB_VERIFIED_INPUT_MANIFEST_SHA256`:
wrapper передаёт её как `psql -v verified_input_manifest_sha256=...` без
автоматической подстановки baseline. Это SHA audit manifest, указанный в
`answers/baseline-manifest.json` как `baseline_audit_manifest_sha256`, **не**
SHA самого файла baseline-manifest.json или manifest CLI W-11. Значение разрешено
передавать только после доказанной CSV↔raw привязки и успешных core-инвариантов
на той же остановленной генерации и том же endpoint. Статическое совпадение hash
само по себе такого доказательства не даёт. Для runtime сверки подготовлен
`scripts/verify-model.py --raw-inputs --dsn-env RWB_VALIDATION_DSN`; DSN задаётся
вне Git и должен указывать на ту же БД, что wrapper. Требования контроля и
фактические ограничения зафиксированы в [answers/RESULTS.md](../answers/RESULTS.md).

`rebuild-check` учитывает каждое значение, NULL и повтор строки в таблицах/views.
Сначала SHA-256 хешируется JSONB каждой строки, затем отсортированный multiset
хешей вместе с отдельным count. Исключена только
`core.check_results.checked_at`: это время запуска, а не бизнес-данные.
Обе успешные сборки коммитятся. При различии command возвращает 1 и печатает diff;
автоматического восстановления первой версии нет. На всё время команды должны
быть остановлены также другие model writers. Для крупного будущего объёма этот
full-content check потребует измерения памяти/времени; benchmark здесь не выполнен.

## Транзакция, ошибки и область очистки

[scripts/build-model.sh](../scripts/build-model.sh) — владелец транзакции:
`psql -X -1 -v ON_ERROR_STOP=1`. `-X` исключает пользовательский `.psqlrc`, `-1`
объединяет DDL, загрузку, mart и финальные инварианты до commit. Includes сначала
проверяются и разворачиваются полностью: отсутствующий файл не вызывает SQL run.
Прямой запуск `build.sql` без условий wrapper отвергается его guard.

Isolation — `REPEATABLE READ`; source timestamps — без timezone по контракту,
формат ISO YMD. `TimeZone=UTC` фиксирует сессию, **не** объявляет timezone источника.
`lock_timeout=5s`, `statement_timeout=10min`, idle-in-transaction timeout — 1min.
Advisory transaction lock `(1667330674, 1)` fail-fast сериализует cooperating model
команды в этой БД. Он **не блокирует текущий loader** и не является raw lock.

[00_schemas.sql](../model/00_schemas.sql) создаёт схемы при отсутствии и удаляет
только перечисленные принадлежащие модели views, таблицы и `core.run_checks()`.
Схемы, их grants и посторонние объекты сохраняются. Views удаляются одной группой,
затем таблицы вместе с внутренними FK. Везде `RESTRICT`; `CASCADE`, `DROP OWNED`
и `DROP SCHEMA` не используются. Внешний зависимый view/FK, неверный тип объекта
или недостаточные права дают ошибку с dependency detail; такую зависимость
разбирают отдельно, а не обходят очисткой. При добавлении owned relation обновить
явный inventory `00_schemas.sql` и проверить повторный build. Пересозданные
таблицы/views получают обычные default privileges роли: прежние grants именно
на этих objects не сохраняются автоматически; дополнительные grants требуют
отдельного явного шага. Права на схемы при этом не сбрасываются.

Нужны SELECT на восемь raw-таблиц, CREATE/USAGE на core/mart и ownership удаляемых
объектов (либо соответствующая роль); для создания схем впервые — CREATE на БД.
Запись/ownership raw wrapper не использует. При неизвестном происхождении
существующих одноимённых core/mart-объектов сначала установить ownership и scope.

Ошибка SQL прекращает исполнение; незавершённая транзакция откатывает изменения,
включая cleanup и новый журнал проверок. Wrapper сохраняет ненулевой `psql` exit
и пишет пояснение после исходного stderr. Exit 2 также используется для неверных
аргументов, отсутствующей предпосылки/файла; отличать их по диагностике.
Ошибка соединения — не доказательство rollback: при разрыве около commit проверить
actual database state до повтора. Автоповтора и reload raw нет.

Пример сохранения stdout/stderr вне Git с корректным exit status, после подготовки:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host bash scripts/build-model.sh build > /tmp/capibara-build.log 2>&1
```

## Протокол эксклюзивной фазы raw

`TRUNCATE` не MVCC-safe: один `REPEATABLE READ` **не** защищает от параллельного
TRUNCATE/DROP/CREATE. Сейчас loader не имеет общего advisory protocol. Вместо
навязанных блокировок raw используется согласованная остановка его writers:

1. Владелец загрузки закрывает reload-фазу: `setup.sh`, `load_raw.py`, ручные
   TRUNCATE/DROP/CREATE/COPY/UPDATE/DELETE raw и другие loaders не запускаются.
   Дождаться завершения уже начатых reload-транзакций. Не завершать чужие процессы.
2. Проверить endpoint/роль и активные подключения совместно с владельцем БД.
   Просмотр `pg_stat_activity` полезен, но отсутствие видимого SQL не доказывает
   отсутствия idle/скрытых/будущих writers. Если остановку writers нельзя
   обеспечить, `RWB_RAW_RELOAD_PAUSED=1` не устанавливать и сборку не начинать.
3. Только после этого установить переменную для выбранной команды. Это явное
   подтверждение оператора, а не проверка загрузчика в коде. Пауза действует до
   выхода **всей** команды; для `rebuild-check` — обе сборки и fingerprints.
4. После завершения проверить exit и логи, лишь затем владелец вновь открывает
   reload-фазу. При failed build raw остаётся прежним; не запускать loader как
   «исправление» ошибки типов или контроля.

Наличие этого протокола не равно его выполнению. Runtime acceptance требует
изолированного PG16 стенда и двух сессий: reload-before-build, build-before-reload,
TRUNCATE и DDL reload, timeout, нарушение паузы и сохранность одного поколения.
Принудительную гонку не воспроизводить на общих данных. Фиксировать точные команды,
транзакционные границы, роли/права и observed result. Эти проверки сейчас pending.

## Типы и качество

[05_typecheck.sql](../model/05_typecheck.sql) до cast проверяет обязательные
идентификаторы, integer format/bounds, finite numeric format/storage bounds и
timestamp format/calendar validity через PG16 `pg_input_is_valid`. NULL в
nullable measures/dates остаётся NULL. Отдельная пустая строка перевода категории
допускается как имя `'pt:'`; NULL-key перевода запрещён. Ключи других сущностей
не могут быть NULL/пустыми/только пробелами; исходные непустые тексты не trim-ятся.

Numeric — unconstrained, без скрытого rounding: `1.234` сохраняется, scale >2
в денежных полях виден как warning. `NaN`, infinity, exponent/whitespace notation,
невалидная дата, timezone suffix и дробные секунды блокируются до model cast.
Timestamp входа — точный `YYYY-MM-DD HH:MM:SS`, hour 00–23, minute/second 00–59;
источник не превращается в zoned instant. Для изменения формата нужна явная
правка контракта, а не ослабление cast ради прохождения теста.

[30_quality.sql](../model/30_quality.sql) пишет только реально найденные аномалии
в `core.data_issues(issue_code, severity, entity_type, entity_key jsonb, details
jsonb)`. PK — первые код/тип/ключ. Chronology, пропущенные даты/children/компоненты,
необычные scores/statuses/installments, отсутствующий вес, нулевые/отрицательные
меры, malformed ZIP, missing category/translation и конфликт payload review_id
являются warnings с сохранением данных. Разница платежей вычисляется после
независимой агрегации children только при полном покрытии компонентов обеих
сторон; sign и comparator записаны. Это наблюдение, не объяснение причины.
Missing category и missing translation — разные issues. Неизвестное не заменяется
измеренным нулём. PK/FK, invalid types и потеря полей/строк — blockers; при rollback
их постоянный журнал не сохраняется, поэтому нужен stderr. Нулевой бизнес-показатель
и отсутствие записи в data_issues сами по себе не доказывают корректность модели.

## Приёмка после разблокировки стенда

Сначала действовать по [dev runbook](dev-environment-20261028.md): guard должен
вернуть 0 до любого нового тяжёлого запуска; текущий 78 не обходить.
На существующем безопасном PG16 стенде после согласования raw-паузы:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host make build check answers rebuild-check
```

Отдельно проверить позднюю намеренную SQL-ошибку: она должна дать ненулевой exit,
оставить raw и предыдущую committed core/mart идентичными; проверить external
dependency rejection, права/таймауты и негативные fixtures владельца W-11.
Контроль 1.234/NaN должен показать сохранённую точность/блокировку соответственно;
NULL/zero, missing child, конфликт review и calendar gaps — собственные outcomes.
SQL runtime, rollback и reload protocol этим документом не объявляются PASS.

Pinned `make control` выполнить отдельно после привязки входа с явной
`RWB_VERIFIED_INPUT_MANIFEST_SHA256`; её нельзя автоматически брать из локального
JSON до live-проверки.

## Выполненные малые проверки W-09

Сверка `2026-10-28T09:37:33Z`: `bash -n scripts/build-model.sh` — exit 0;
`make -n build check control answers manifest rebuild-check` — exit 0;
`make manifest` — exit 0, восемь pinned CSV / 550 759 records;
`python3 scripts/verify-model.py --plan` — exit 0, 16 cases, missing stages `[]`,
status `pending_db_execution`.

Статический скан сверил восемь includes, точный cleanup inventory 24 созданных
core/mart tables/views/functions, 36 precheck-ссылок на реальные raw columns,
отсутствие raw writes/CASCADE/COMMIT/ROLLBACK в фрагментах и trailing whitespace.
Это текстовая проверка, не PostgreSQL parser.

Малый временный harness с подставными `psql`/`docker` проверил семь путей wrapper:
запрет без raw-паузы; host flags/includes и возврат client exit 17; отдельный check
без reset; Docker stdin без startup/copy; answer variants; неверные mode/command.
Реальные клиенты и БД этим harness не вызывались, временные файлы удалены.
После подключения параметра контроля отдельно проверены отказ без verified hash
и передача явно заданного hash подставному клиенту. Данных из core, DB rollback,
negative fixture outcomes и SQL runtime PASS в этом evidence нет.

Основания: [проектный brief](implementation-brief-20261028.md), research
[S08–S11](../research/internet-2026-10-28/synthesis/selected-findings.md),
[PG16 psql](https://www.postgresql.org/docs/16/app-psql.html),
[PG16 input validation](https://www.postgresql.org/docs/16/functions-info.html#FUNCTIONS-INFO-VALIDITY),
[PG16 TRUNCATE](https://www.postgresql.org/docs/16/sql-truncate.html).
