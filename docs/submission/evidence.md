# Доказательства и приёмка комплекта

Это перечень свидетельств сдачи W-12. Каноническая карта задач — [workstreams](../workstreams.md), решения — [decision-log](../decision-log.md). Ни один baseline ниже не является результатом PostgreSQL/core W-12.

Код и исходный комплект опубликованы: main `aca34f5b693b794fc2a0ea8c2623293b462b6089`. Приняты раздельные факты/общие справочники, все review-order связи, delivered revenue без freight, order GMV с freight, обе populations Q1/Q2, весь snapshot Q2–Q5, аномалии без догадок и область/HTML дашборда. Late/reviewweight/smoothing открыты.

## Ответы Q1–Q10

В [tasks](../../hack-context/hackathon-students/docs/tasks.md) прочитаны Q1–Q5. Для каждого ответа нужны: точный SQL/ref, grain, status, окно, компоненты, знаменатель, NULL/coverage, единицы, полный экспорт и run ID. Состояние CSV/raw baseline отличается от состояния ответа из модели.

| Вопрос | Контроль/вариант из источников | Что должно быть в окончательном результате | Core/DB evidence |
|---|---|---|---|
| [Q1: месяцы](../../answers/q01.sql) | 24 месяца; выручка 13 221 498.11; placed 99 421 / delivered 96 478 в окне | Все месяцы `[2016-09-01,2018-09-01)`, оба count с именами | pending |
| [Q2: продавцы](../../answers/q02.sql) | Top revenue 226 987.93; top delivered orders/units 1 124/1 148, all 1 132/1 156 | 10 продавцов, исходные город/штат, tie-break, seller-only item amounts | pending |
| [Q3: чек](../../answers/q03.sql) | Order item+freight 159.88; avg source rows/units 1.142; groups product×seller 1.039 | Точный numerator/denominator до округления; payment average отдельным именем | pending |
| [Q4: покупатели](../../answers/q04.sql) / [окно Q1](../../answers/q04_window.sql) | Весь снимок: 96 096, повторных 2 997, 3.12%; окно Q1: 96 090, 2 987, 3.11% | Устойчивая buyer identity, оба окна/статусы подписаны | pending |
| [Q5: категории](../../answers/q05.sql) | 74 используемые группы; top 1 233 131.72; total 13 221 498.11 | Unknown сохранён; missing translation отдельно; сумма и доли при одном фильтре | pending |
| Q6 | Условие ещё не опубликовано | Паспорт→SQL из модели→результат→check | pending: условие |
| Q7 | Условие ещё не опубликовано | Паспорт→SQL из модели→результат→check | pending: условие |
| Q8 | Условие ещё не опубликовано | Паспорт→SQL из модели→результат→check | pending: условие |
| Q9 | Условие ещё не опубликовано | Паспорт→SQL из модели→результат→check | pending: условие |
| Q10 | Условие ещё не опубликовано | Паспорт→SQL из модели→результат→check | pending: условие |

Источник чисел и оговорок: [implementation brief, вопросы 2–5, 14–15](../implementation-brief-20261028.md), [S04/S12](../../research/internet-2026-10-28/synthesis/selected-findings.md), [профиль](../profiling.md). Если экспорт не совпал, сохраняем расхождение и проверяем формулу/популяцию; не переписываем raw или baseline ради совпадения.

## Уже готовое к первому чекпоинту

Код W-08…W-11 завершён по сообщению координатора; файлы сборки, 7 dims +4 facts, mart/answers/checks и тестовые инструменты доступны в общем checkout. Код опубликован. Отдельно выполнены 16/16 малых PostgreSQL cases; это не full Olist acceptance. [Сценарий 13:30](checkpoint-1330.md) содержит точные команды и реальные ожидаемые выходы.

| Проверка | Уже получено | Источник и предел |
|---|---|---|
| Manifest/isolation unittest | 14 tests, exit0 | Независимый повтор координатора по прямому сообщению; [тесты](../../tests/model/test_input_manifest.py) и [safety tests](../../tests/model/test_verify_model.py); не PostgreSQL |
| Synthetic mart/answer SQL | 93 checks, exit0 | [W-10 report](../../answers/verification.json), независимый повтор координатора сообщён; DuckDB1.5.2, 128MB in-memory, не core build |
| Static | 19 files, exit0 | [static-check.py](../../answers/static-check.py), повтор координатора сообщён; синтаксис Python, JSON, ссылки и хеши |
| Wrapper | Dry-run, exit0 | [Runbook W-09](../build-runbook.md#выполненные-малые-проверки-w-09), повтор координатора сообщён; подставные клиенты, не БД |
| PostgreSQL 16.15 synthetic runtime | 16/16: 4 положительных +12 ожидаемых отказов; fixture CLI 0.944424 s | W-14: [pg-smoke.md](../../research/implementation-review-20261028/pg-smoke.md), [JSON](../../research/implementation-review-20261028/pg-smoke.json). Сервер остановлен; full Olist/build.sql wrapper/lifecycle не проверены |
| PostgreSQL fixture plan | 16 cases, missing stages [], exit0 | `--plan` сам по себе не исполняет cases; runtime evidence находится в отдельной строке выше |
| Один связанный заказ | CSV-чтение exit0, 1 item /3 payments /1 review; GMV и payment38.71 | Выполнено W-12: [результат](order-example.json), [скрипт](order-example.py); mapping в core описан, SQL не исполнен |

Для независимого повторения координатора отдельный run-log/ref в поручении не указан. Поэтому его результаты названы сообщением координатора; W-12 не создаёт ложное свидетельство своего выполнения. Owner-отчёты и snapshots хешей доступны отдельно.

## Независимый review

[Astra review](../../research/implementation-review-20261028/astra-review.md) завершён: **1 P1 + 4 P2**, P0 не найден. Разделение grains и основная семантика поддержаны прочитанным кодом и малым PG evidence. Это review конкретного input snapshot, не будущих исправлений. Координатор ведёт фиксы отдельно; W-15 их не меняет и не объявляет закрытыми.

- **R1/P1:** CSV→raw verifier создаёт TEMP внутри READ ONLY; блокирует binding/lifecycle path, не доказывает неправильную модель.
- **R2/P2:** самопроверка translation membership не защищает `has_translation_row`.
- **R3/P2:** LIMIT 10 в Q2 скрывает кандидатов с неполной выручкой.
- **R4/P2:** lifecycle-команда не устанавливает обязательный verified-manifest token.
- **R5/P2:** whitespace-only keys проходят проверку `btrim` для табуляции/перевода строки.

Методы и точные repro различаются: static/официальная PG семантика и узкие DuckDB probes; полного PG lifecycle reviewer не запускал. [Машинное evidence](../../research/implementation-review-20261028/astra-evidence.json). До full-data acceptance нужны исправления, повторные целевые проверки и полный прогон.

## Сборка и проверки

| Входная точка | Роль | Доказательство выполнения |
|---|---|---|
| [model/CONTRACT.md](../../model/CONTRACT.md) | Точные имена/grains/NULL/typing | Прочитан W-12, без DB execution |
| [build-model.sh](../../scripts/build-model.sh), [build.sql](../../model/build.sql), [runbook](../build-runbook.md) | Wrapper владеет транзакцией, single-transaction/fail-fast; raw reload pause — утверждение оператора, не автоматическая блокировка loader | Код прочитан, DB pending |
| [10_dims](../../model/10_dims.sql), [20_facts](../../model/20_facts.sql), [05_typecheck](../../model/05_typecheck.sql), [30_quality](../../model/30_quality.sql) | Детали, типы и наблюдаемые аномалии | Малые PG cases PASS; полная Olist-сохранность pending |
| [40_mart](../../model/40_mart.sql), [50_answers](../../model/50_answers.sql), [паспорта](../metric-definitions.md) | SQL метрик и ответов, варианты с coverage | DuckDB93 +PG small cases; full-data exports pending |
| [90_checks](../../model/90_checks.sql), [verify-model.py](../../scripts/verify-model.py), [input-manifest.py](../../scripts/input-manifest.py) | Инварианты, проверки и версия входа, отдельно от известных ответов | Код доступен; малые PG cases PASS; CSV↔raw и полный runtime pending |
| [control.sql](../../answers/control.sql), [baseline manifest](../../answers/baseline-manifest.json) | Pinned regression после доказанного live input binding | Binding и control execution pending |
| [answers/verification.json](../../answers/verification.json), [RESULTS](../../answers/RESULTS.md) | Owner W-10 записал 93 offline checks, DuckDB 1.5.2, synthetic fixture; PostgreSQL/core flags false | Отчёт прочитан W-12, не повторён; соответствие хешей — в snapshot |
| [Dev runbook](../dev-environment-20261028.md) | Предварительная проверка окружения; не замена сборке | По handoff W-07 offline exit0, обычный exit3 на Docker; W-12 не повторял |
| [scripts/dev-check.sh](../../scripts/dev-check.sh) | Read-only readiness окружения | DB readiness pending |

### Матрица runtime-приёмки

| Gate | Что должно произойти | Что сохранить |
|---|---|---|
| Вход и версия | 8 CSV/ref/hash/header/count связаны с конкретным поколением raw | Input manifest, loaded generation, PG version, SQL SHA |
| Чистая сборка | Один запуск создаёт полный core/mart; raw неизменен | Команда, stdout/stderr, exit, число строк и checks |
| Повтор | Те же входы дают эквивалентные детали и метрики | Сравнение полей/ключей, NULL и сумм; техническое время запуска отдельно |
| Сохранность | Все восемь источников имеют mapping; проверены ключи, поля и связи | Multiset/NULL-aware сверка, сироты, unmatched contexts, календарные gaps |
| Деньги | Независимые totals, coverage, полнота price/freight/payment | Both/items_only/payments_only/neither; exact и tolerance с одинаковым предикатом |
| Негативные проверки | Fanout 2×2×3, no-child/NULL/0, новый статус, review conflict, cast/scale, gap date, +10/−10 | Изолированные fixtures и ожидаемая политика; исходный raw не менять |
| Атомарность | Ошибка в конце не оставляет частичный core/mart; raw не меняется | Ненулевой exit, состояние до/после, отдельный лог ошибки |
| Параллельная загрузка | Согласованное поколение; доказан loader/build protocol и timeout | Оба порядка гонки reload/build на отдельном стенде |
| Ответы и показ | Все Q1–Q10 из модели, UI при одинаковых фильтрах даёт те же компоненты | SQL, exports, метрики, фильтры, run ID; отсутствие runtime не скрыто |

`REPEATABLE READ` сам по себе не доказывает защиту от TRUNCATE raw. Check table внутри неуспешной транзакции откатится; stderr и отдельный check-run нужны для диагностики. `CASCADE` допустим только в проверенной зоне owned objects и зависимостей. Эти пункты — план проверок, не PASS.

## Как фиксировать настоящий run

В отдельном evidence-каталоге сохранить `run.json` со следующими полями: UTC, repository/commit и хеши dirty SQL, input manifest SHA, raw generation, PostgreSQL version, точная команда, exit code, относительные stdout/stderr/answer paths, checks passed/failed/skipped, параметры метрик. Без секретов, исходных CSV, зависимостей и runtime-dump базы. Конкретное хранилище evidence выбирает владелец build/checks; W-12 не создаёт параллельный registry.

Шаблон описания свидетельства:

```text
method: static | CSV | fixture | PostgreSQL | UI
input_ref / sql_sha256 / run_id:
command:
observed_exit / observed_result:
expected:
limitations / pending:
```

## Следующий шаг

На текущем Mac известен guard exit78 (свободно 30.42 GiB <35, memory pressure2), Docker daemon отсутствует. Это переданная информация, W-12 не запускал preflight, Docker, VM, установку или fixtures. Новая тяжёлая работа до снятия ограничений запрещена. Решения о другом стенде принадлежат координатору; не обходить guard.

**Сейчас, без БД, из корня checkout:**

```sh
python3 docs/submission/verify_pack.py
```

Команда проверяет локальные ссылки, переносимость HTML и manifest W-12; это static check, не SQL runtime.

**Точная команда следующего DB-этапа**, только на разрешённом уже работающем PostgreSQL-стенде, с настроенным правильным libpq endpoint и подтверждённой остановкой всех raw/model writers на всё время команды:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host make build check answers rebuild-check
```

Она взята из [runbook владельца W-09](../build-runbook.md), W-12 её не выполнял. `make check` обновляет check_results, это не read-only. `rebuild-check` коммитит две сборки и не доказывает rollback. Pinned `make control` отдельно требует доказанного CSV↔live raw binding на той же генерации и `RWB_VERIFIED_INPUT_MANIFEST_SHA256`; не подставлять hash просто потому, что он известен из JSON.

**После готовности разрешённого стенда:** readiness из dev-runbook → штатный build owner command → независимые checks/control → повтор/rollback/negative gates → экспорты Q1–Q10 → сравнение показа с SQL. Не запускать `setup.sh --reset` в общем окружении как часть сдачи без точного разрешения.

## Проверка материалов W-12

Фактически выполненные команды, результаты и хеши находятся в [handoff.md](handoff.md) и [manifest.sha256](manifest.sha256) после финальной статической проверки. [input-evidence.json](input-evidence.json) фиксирует конкретные прочитанные байты чужих артефактов и сверку с hashes в offline-отчёте; позднейшие правки owners требуют новой сверки. Готовность к review документации не равна финальной готовности проекта.
