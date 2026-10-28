# Результаты ответов

**Статус: `not executed from core`.** SQL реализован; фактические ответы
PostgreSQL/core пока отсутствуют. Ниже отдельная колонка CSV reference,
а не результат нашей модели и не DB PASS.

| Вопрос / вариант | Результат из core | CSV reference / контроль | Определение |
|---|---|---|---|
| Q1 | not executed from core | 24 месяца; 99 421 placed; 96 478 delivered; 13 221 498.11 BRL | покупка Sep2016–Aug2018, price без freight, оба counts |
| Q2 | not executed from core | top revenue 226 987.93; 1 124 delivered orders / 1 148 units; all-status 1 132 / 1 156 | только позиции своего продавца, весь снимок |
| Q3 item+freight | not executed from core | 159.88 BRL, n=96 478 | среднее order_gmv, не среднее по позициям |
| Q3 payment comparator | not executed from core | 159.86 BRL, n=96 477 | отдельная сумма и отдельный знаменатель |
| Q3 строки / единицы / product×seller | not executed from core | 1.142 / 1.142 / 1.039 | три именованные метрики, округление до 3 знаков |
| Q4 весь снимок | not executed from core | 96 096 buyers; 2 997 repeat; 3.12% | все статусы; customer_unique_id; абсолютное число и доля |
| Q4 окно Q1 | not executed from core | 96 090 buyers; 2 987 repeat; 3.11% | повторность пересчитана после фильтра окна |
| Q5 | not executed from core | 74 категории; top health_beauty 1 233 131.72; total 13 221 498.11 BRL | unknown отдельно от known category без перевода |
| Payment exact | not executed from core | 639; signed −1 819.51 BRL; absolute 7 981.47 BRL | Δ=payment−GMV, Δ<>0, единая population count/sums |
| Payment >0.01 | not executed from core | 366; signed −1 818.84 BRL | abs(Δ)>0.01, без округления до predicate |
| Payment coverage | not executed from core | both 98 665; items_only 1; payments_only 775; neither 0 | наличие строк, не сумма денег; полнота компонентов отдельно |
| Reviews | not executed from core | 99 224 пары; 98 410 IDs; 0 конфликтов payload | все пары сохранены; pair/ID/order weights раздельно |
| Q6–Q10 | pending task publication | ещё не опубликованы | формулировки не выдуманы |

Определения: [паспорта](../docs/metric-definitions.md).
Источник reference: опубликованный synthesis
`1939068295d7203a15cbb0a1ab5d407caca90f58:docs/idea-synthesis.md`,
финальный research `72c1fb6ffe43e95b2ba539dc1b396374f4bfde3a`,
[CSV audit manifest](../research/data-audit-2026-10-28/manifest.json).
Ошибочная смешанная пара «366 / −1 819.51» не используется как контроль.

## Вход и контрольные цифры

[baseline-manifest.json](baseline-manifest.json) фиксирует 8 CSV hashes,
Olist ref `d9e49802f3e92d09ee94ab9ccc5e457f207a8959` и hash исходного
audit manifest:
`8afb8691d866ef5f5ed465eb9111df521408e1b3d84408d5f0c03337477312c3`.
Это идентификация CSV reference. Соответствие текущему raw и его core build
ещё **не установлено**. Manifest JSON не доказывает, что база загружена из
этих CSV. После смены входа oracle выбирается заново явно.

[control.sql](control.sql) отделён от сборки. Он требует параметр
`verified_input_manifest_sha256`: передавать его разрешено только после
проверяемой привязки live raw/core к этому набору входов. Без параметра
скрипт прекращает работу SQL-ошибкой с кодом psql 3; несовпадение контролей
также вызывает SQL-ошибку с кодом 3 (ON_ERROR_STOP).
Эти ветви пока не исполнялись в psql.

## Что проверено

`python3 answers/check_offline.py --report answers/verification.json`
проверяет реальные SQL-файлы parser/binder установленного DuckDB и малую
in-memory synthetic fixture: fanout 2×2×3, календарь, пустой набор,
четыре класса покрытия, NULL/partial/zero, cent boundary, signed/absolute
comparator, buyer window, unknown/translation, конфликт NULL/empty payload,
review weights и отдельные day/timestamp/min/max правила.
Точные checks и hashes файлов — [verification.json](verification.json).
Fixture не читает CSV/raw, не запускает core builder и не создаёт стенд.
DuckDB отличается от PostgreSQL, в том числе NUMERIC/AVG и диалектом SQL.
Это **offline evidence**, не PostgreSQL parsing/runtime PASS.

## Что ещё выполнить

Блокеры PostgreSQL runtime: сообщённый ресурсный guard preflight=78 и
недоступный Docker daemon; обход, VM, Docker и тяжёлые сборки не запускались.
После предоставления разрешённого PostgreSQL 16 стенда владелец сборки
должен выполнить clean build, checks, повтор, rollback и manifest binding.
Затем сохранить **полные вычисленные** Q1/Q2/Q5 таблицы и строки Q3/Q4,
payment/review variants, stdout/stderr/exit code и build/input SHA.

Точные команды после успешной сборки (DATABASE_URL задаётся стендом):

```sh
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f answers/q01.sql
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f answers/q02.sql
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f answers/q03.sql
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f answers/q04.sql
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f answers/q04_window.sql
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f answers/q05.sql
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f answers/payment_reconciliation.sql
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 -f answers/review_weights.sql
```

Только после доказанной привязки live input к pinned manifest:

```sh
psql "$DATABASE_URL" -X -v ON_ERROR_STOP=1 \
  -v verified_input_manifest_sha256=8afb8691d866ef5f5ed465eb9111df521408e1b3d84408d5f0c03337477312c3 \
  -f answers/control.sql
```

AI provenance: W-10 Codex написал SQL/паспорта/fixture по brief и CONTRACT;
синтетические checks выполнены самим автором. Независимая проверка и
человеческое принятие этой реализации ещё не заявлены.
