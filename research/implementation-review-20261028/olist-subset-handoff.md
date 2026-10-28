# Реальный ограниченный Olist: 1 000 заказов

UTC handoff update: 2026-10-28T10:42:19.773034+00:00. Repository `kiruha355/rwb_hak`, shared branch `main`,
local base `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`.
Owner: delegated bounded-real-Olist implementation; publication remains with W-01.
Status: `ready_for_review`, local runtime checks passed; remote publication not claimed.

[Standalone HTML](../../dashboard/olist.html) содержит настоящую выгрузку `core`/`mart`
из PostgreSQL 16.15. Синтетический `DEMO_DATA` из этой страницы удалён.
Это специально стратифицированная выборка 1 000 из 99 441 заказов;
она не является репрезентативной и не заменяет проверку полного Olist.

## Объём и сохранение данных

| Таблица raw | Строк |
|---|---:|
| orders | 1 000 |
| order_items | 1 121 |
| order_payments | 1 037 |
| order_reviews | 996 |
| products | 913 |
| sellers | 491 |
| customers | 1 000 |
| product_category_translation | 71 |
| Всего | 6 629 |

Алгоритм детерминирован: два обязательных реальных примера, минимум SHA256(order_id)
по каждой наблюдаемой паре месяц/статус, по два заказа для 25 повторных покупателей,
затем заполнение до 1 000 минимальными SHA256(order_id). Взяты все дочерние строки
выбранных заказов и все необходимые строки справочников. Подробности, исходный ref,
8 исходных и 8 subset SHA256: [input manifest](olist-subset-input.json).

CSV и файлы новой отдельной БД сохранены вне репозитория. Основной marketplace,
исходные CSV, чужие БД и Docker не изменялись. Запуск полного набора не выполнялся.
После проверки остановлен только запущенный задачей экземпляр tiny PostgreSQL;
данные БД сохранены. HTML работает без БД.

## Фактически выполнено

- Все 8 полных исходных CSV совпали с pinned SHA256 до и после работы.
- Независимая потоковая сверка selected-source/subset сохранила все строки,
  включая различие CSV между NULL и quoted empty: [source equality](olist-subset-source-equality.json).
- 8/8 subset CSV/raw: двусторонний `EXCEPT ALL`, multiplicity и `_source_file`:
  [raw verification](olist-subset-raw-verification.json).
- `build`, `check`, `answers`, `rebuild-check` — exit 0; повторные fingerprints совпали:
  [build](olist-subset-build.json).
- 201 model invariant: 0 ошибок, 0 предупреждений:
  [validation](olist-subset-validation.json).
- После всех стадий внедрена реальная поздняя SQL-ошибка `22012`; rollback сохранил
  fingerprints всех raw/core/mart relations: [rollback](olist-subset-rollback.json).
- Выгружены все 1 000 заказов, 1 121 позиций, 996 связей отзыв—заказ;
  сумма payment counts — все 1 037 платежей. Календарь содержит 26 месяцев,
  Q01 использует оговорённое окно из 24 месяцев, включая пустой ноябрь 2016.
  Отсутствующий платёж остаётся NULL. Strong export gate проверил имя БД,
  code hashes, counts и SHA256 canonical payload: [export check](olist-subset-export-check.json).

[Точные Q01–Q05 из модели](olist-subset-answers.json): 882 delivered-заказа,
выручка позиций выборки 106 350.48 BRL, средний чек с доставкой 142.35 BRL,
975 покупателей, 25 повторных. Эти числа относятся только к выборке.

## Воспроизводимые команды

Подготовка/загрузка требуют отдельно разрешённого пустого endpoint этой задачи;
скрипт проверяет cluster path, Unix socket и лимит buffers, запрещает overwrite
существующей raw/core/mart. Он не запускает сервисы и не устанавливает пакеты.
На уже созданном runtime повторный `prepare`/`load` намеренно откажет в overwrite.

```sh
python3 scripts/build-olist-subset.py prepare
python3 scripts/build-olist-subset.py load
python3 scripts/build-olist-subset.py verify
python3 scripts/build-olist-subset.py build
python3 scripts/build-olist-subset.py report
python3 scripts/build-olist-subset.py rollback-check
# PGHOST/PGPORT/PGDATABASE/PGUSER задаются для выделенного endpoint;
# PGSERVICE и DATABASE_URL должны быть сняты, если относятся к другой БД.
python3 dashboard/export_data.py \
  --dataset-label 'Olist · 1 000 реальных заказов · ограниченная выборка' \
  --output "$RWB_SUBSET_RUNTIME/model.json" \
  --html dashboard/olist.html \
  --validation-report research/implementation-review-20261028/olist-subset-validation.json
```

Первый build остановился до SQL из-за `PGSERVICE=''` (`definition of service "" not found`,
exit 2). Исправлен только wrapper окружения: переменная полностью удаляется;
последующие четыре команды успешно выполнены. Автоматического raw reload не было.

## Границы и следующий шаг

Полный DB load, full-population pinned controls и browser/visual acceptance этим owner
не выполнялись. Frontend проверяет и показывает координатор. Следующий шаг W-01:
показать реальную страницу, зарегистрировать handoff и опубликовать готовые code/HTML/metadata.
Не публиковать runtime CSV, DB или полные runtime logs.

Final HTML SHA256: `a63c754d5ef6d626683d7cc64341ef05553fc5df20323c0e48579f012321f509`.
Canonical data SHA256: `ad80d501a86c47e6a7b18e6dbc1598cd4057ff710da8a61b3f2b5558ff1ba06e`.
Validation report SHA256: `352f228cfb6b2a298afe2d69246bc1767e11d1f071f6c09dc45edf4d88a793af`.
