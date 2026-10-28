# W-10 handoff

Статус: **ready_for_review, PostgreSQL runtime pending**.
Ни commit/push, ни remote SHA этой порции не создавались.
Input main: `1939068295d7203a15cbb0a1ab5d407caca90f58`;
research: `72c1fb6ffe43e95b2ba539dc1b396374f4bfde3a`.
Ownership: только `model/40_mart.sql`, `model/50_answers.sql`, `answers/**`,
`docs/metric-definitions.md`. Общие реестры и explainer не менялись.

## Реализовано

- Паспорта и `mart.metric_definitions`: grain, formula, population/status,
  date/window, denominator, NULL, units, additivity.
- `v_orders` независимо агрегирует items/payments/reviews до order grain;
  `v_order_items` соединяет только many-to-one dimensions/order.
- Сверка платежей: order-level и status×4 coverage classes; non-NULL component
  counts, строгие суммы и known subtotals, exact / >0.01 / =0.01,
  count и signed/absolute sum одного predicate.
- Отзывы: все варианты payload доступны; при конфликте один ID не получает
  произвольный payload. Pair/ID/order weights с numerator/denominator/exclusions.
- Именованные day/timestamp и min/max deadline варианты; интервалы исключают
  только нарушенную пару timestamp. Причины, вина, выкуп и денежный ущерб
  не выводятся.
- Q1 календарь 24 месяца, оба counts; Q2 delivered и all-status counts;
  Q3 order GMV и payment comparator с разными n, source rows/units/distinct
  product×seller; Q4 весь snapshot плюс отдельное окно; Q5 все категории,
  unknown отдельно от missing translation. Q6–Q10 documented pending.
- CSV reference отделён от фактических результатов; pinned oracle находится
  вне build. `RESULTS.md` сохраняет `not executed from core`.

Точные пути и SHA256 каждого файла этой порции, включая этот handoff:
[sha256.json](sha256.json). Контракт core прочитан перед зависимой реализацией;
его hash сохранён в [verification.json](verification.json), сам CONTRACT
не входит в owned changes.

## Выполненные проверки

```sh
python3 answers/check_offline.py --report answers/verification.json
```

Exit 0: DuckDB 1.5.2, **93 checks**, `postgresql_executed=false`.
Реальные 40/50 SQL parsed (14+12 statements) и bound без переписывания.
Малая in-memory fixture проверяет fanout 2×2×3, пустые populations,
календарь, NULL/partial/zero, четыре покрытия, точный cent boundary и
0.0101 до округления, matching count/net/absolute predicates, разные n,
buyer identity/window, unknown/translation и NULL/empty review conflict.
42 выражения pinned oracle связываются; synthetic input не проходит oracle.
psql-only branches oracle не выполнялись.

Отдельная static-проверка Python syntax, JSON, trailing whitespace,
relative documentation links и hashes verification — exit 0.
Команда сохранена в [static-check.py](static-check.py).

Это **не** PostgreSQL parser/runtime, не проверка настоящего core,
не Olist/CSV вычисление и не DB controls/rollback/rebuild PASS.
Fixture закрывается; серверы, файлы DB, зависимости и установки не создаются.

## Непроверенное и блокеры

На входе сообщены: guard preflight=78, SSD 30.42 GiB <35,
memory pressure=2; Docker daemon отсутствует. Здесь guard не обходился,
Docker/VM не запускались, тяжёлые fixtures/build не создавались.
Живого PostgreSQL исполнения не было. Clean build, PostgreSQL semantics,
core invariants, real answers, raw↔CSV binding, controls, rollback и повторная
сборка остаются pending. Авторство AI не означает independent/human review.

Контроль требует **доказанной** live raw/core привязки к audit manifest
`8afb8691d866ef5f5ed465eb9111df521408e1b3d84408d5f0c03337477312c3`.
Хеш JSON и присутствие CSV не устанавливают её автоматически.

## Следующая точная команда

Без runtime сейчас:

```sh
python3 answers/check_offline.py --report answers/verification.json
python3 answers/static-check.py
```

На предоставленном PostgreSQL 16 стенде, после выполнения reload-barrier
протокола [build runbook](../docs/build-runbook.md) и выбора нужного endpoint:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host PGSERVICE=capibara make build
```

`PGSERVICE=capibara` должен быть заранее настроен владельцем стенда.
Здесь команда **не запускалась**; отсутствие такого сервиса не разрешает
молча подключаться к другой БД. После successful build/raw binding:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host PGSERVICE=capibara \
  RWB_VERIFIED_INPUT_MANIFEST_SHA256=8afb8691d866ef5f5ed465eb9111df521408e1b3d84408d5f0c03337477312c3 \
  make control
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host PGSERVICE=capibara make answers
```

Публикация и итоговая независимая приёмка — W-01/родитель.
