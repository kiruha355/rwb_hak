# Проверка сохранности модели · W-11

Repository `kiruha355/rwb_hak`; вход main
`1939068295d7203a15cbb0a1ab5d407caca90f58`, research
`72c1fb6ffe43e95b2ba539dc1b396374f4bfde3a`.
Контракт — [model/CONTRACT.md](../model/CONTRACT.md). Автор кода и проверки:
Codex / Sol, 2026-10-28. Git index/публикацию ведёт W-01.

**Фактический статус: CSV и малые offline-проверки выполнены; PostgreSQL,
fixtures, clean build/rebuild/rollback и ответы из core не исполнялись.**
Локальный запуск запрещён действующим resource guard (код 78), Docker daemon
недоступен. Эти ограничения не обходились; сервисы/VM не запускались.

## Три разных слоя доказательства

1. **CSV:** [input-manifest.py](../scripts/input-manifest.py) проверяет восемь
   файлов по [закреплённому manifest](../tests/model/input-manifest.lock.json):
   immutable source ref/URL, SHA256 исходных байтов, размер, точный порядок header
   и число логических CSV-записей. BOM/CRLF входят в хеш; перенос внутри кавычек
   не становится новой записью. Файл хешируется тем же потоком, который разбирает
   CSV parser; изменение файла во время чтения обнаруживается по stat.
   Источник pin — опубликованный CSV audit и повторная проверка локальных хешей;
   source ref `d9e49802f3e92d09ee94ab9ccc5e457f207a8959`, всего 550 759 строк.
   Никакой загрузки сети или БД этот шаг не выполняет.
2. **CSV → фактический raw:** `verify-model.py --raw-inputs` сначала требует pin,
   затем использует PostgreSQL CSV parser и временные таблицы, сравнивая все
   бизнес-колонки через `EXCEPT ALL` в обе стороны. Это сохраняет различие между
   unquoted empty/NULL и quoted empty/text, которое Python `csv.reader` не хранит.
   Проверяется `_source_file`; `_loaded_at` не является исходным бизнес-полем.
   Нужны существующее подключение и остановленные на время проверки raw writers.
   Сначала отдельная транзакция создаёт только пустые session-private TEMP
   tables с `ON COMMIT PRESERVE ROWS`. Затем сравнение идёт в `REPEATABLE READ
   READ ONLY`: COPY пишет только в уже существующие TEMP tables; raw не меняется.
   При закрытии соединения временные объекты исчезают. `CREATE TEMP` внутри
   read-only запрещён PostgreSQL, поэтому фазы разделены. Полный pinned binding
   остаётся **pending**, он не подтверждает core по наличию кода.
3. **raw → core → порядок агрегации mart:** [90_checks.sql](../model/90_checks.sql)
   сравнивает типизированные значения согласно контракту. Ни значения ответов,
   ни количество строк конкретного снимка не являются business invariants.
   Контрольные цифры остаются в `answers/control.sql` у W-10.

Manifest включает только восемь объявленных входов; посторонние CSV не становятся
входами автоматически. При изменении источника сравнение должно завершиться
ошибкой. Обновление pin требует отдельной осмысленной проверки нового снимка,
а не перезаписи lock-файла результатом неуспешного запуска. Совпадение CSV не
доказывает, что именно эти байты уже загружены в raw: для этого нужен второй шаг.

## Что проверяет SQL

`core.run_checks()` пересчитывает `core.check_results`. Сейчас это **201 правило**:
16 mapping-наборов × 11 проверок и 25 отдельных правил.

| Область | Проверка и ошибка, которую она отличает от PASS |
|---|---|
| Все 8 источников | Явные проекции каждого бизнес-поля, включая адрес/context заказа, измерения продукта, полный текст и обе даты отзыва, неиспользуемые customer contexts и переводы |
| Каждый mapping | Число строк; key sets в обе стороны; кратность каждого ключа; обязательность/уникальность ключей отдельно в источнике и модели; полный multiset значений в обе стороны; NULL-профиль каждой колонки |
| Типизация | Сравнение после документированных casts без scale rounding; нечисловые/невалидные значения блокируются precheck, non-finite numeric дополнительно проверяется в core |
| Деньги | Суммы, количество известных значений и известных нулей: позиции по заказу/продавцу/категории и целиком; платежи по заказу/типу и целиком. +10/−10 на разных заказах не скрываются общей суммой |
| Независимые children | Наборы заказов без items/payments/reviews; `mart.v_orders` содержит каждый заказ ровно один раз, корректные child counts, полные суммы и четыре состояния payment coverage. No child, all NULL, partial и known zero различимы |
| Связи | Заказ→customer context с buyer identity, buyer, status; context→buyer; item→order/product/seller; payment/review→order; product→category. NULL mandatory FK тоже является нарушением |
| Категории | Полный domain products UNION translations плюс unknown; `pt:` исключает collision с unknown; отсутствующая категория и непереведённое PT-имя сохраняют разные состояния |
| Календарь | Все исходные date roles и минимальное окно Q1 покрыты; сравниваются обязательные дни/атрибуты, отдельно проверяются разрывы между соседними днями. Внешнее расширение календаря допустимо, внутренние gaps — ошибка |
| Новые данные | Неизвестный статус сохраняется без выручки и получает warning. Разные payload одного review ID на разных order pairs сохраняются; FD warning не выбирает один payload. Duplicate pair — ошибка |

Технические lineage-колонки остаются в raw согласно контракту. Лексическое
`'01'` → integer `1` допускается типизацией; тихое изменение денежного значения,
NULL, адреса или связи не допускается. Ключ translation проверяется через
`'pt:' || product_category_name`, поэтому пустое, но известное имя категории
не схлопывается в unknown.

Каждое правило записывает `expected`, `actual`, `ok`, `severity`, `checked_at`.
Ошибка выполнения самого правила считается error, даже если правило было warning.
После сбора ошибок используется `RAISE EXCEPTION`, а не отключаемый `ASSERT`.
`DETAIL` содержит имена, число нарушений и детерминированные примеры. Транзакционный
rollback удалит новые check_results, поэтому stderr/лог ошибки — обязательное
доказательство. При warning успешная сборка сохраняет данные и строки диагностики;
warning не равен доказанной причине аномалии или business approval.

## Выполнено здесь

```bash
python3 -m unittest discover -s tests/model -p 'test_*.py' -v
python3 -m py_compile scripts/input-manifest.py scripts/verify-model.py tests/model/test_input_manifest.py tests/model/test_verify_model.py
bash -n tests/model/validate-lifecycle.sh
python3 scripts/input-manifest.py --verify-pinned --output /tmp/rwb-w11-input-manifest.json
python3 scripts/input-manifest.py --verify-pinned --compare /tmp/rwb-w11-input-manifest.json --output /tmp/rwb-w11-input-manifest-repeat.json
python3 scripts/verify-model.py --plan
```

Результаты: 14 offline unit tests — OK; Python compile и Bash syntax — exit 0;
два manifest-запуска — exit 0, 8 хешей/header/count совпали с pin; план сообщает
`pending_db_execution`, 21 сценарий, missing stages `[]`. Offline tests проверяют
повреждённый CSV, изменение bytes без изменения count, header/order, отсутствие
файлов, unsafe/duplicate manifest entries, изменение ref, schema rebinding,
запрет transaction terminators и соответствие inventory диагностике.
Это не PostgreSQL SQL parser и не доказательство выполнения PL/pgSQL.

## Изолированные негативные SQL-сценарии · pending

[base.sql](../tests/model/fixtures/base.sql),
[assert-base.sql](../tests/model/fixtures/assert-base.sql) и
[cases.json](../tests/model/fixtures/cases.json) исполняются только runner-ом.
Он привязывает **все** `raw./core./mart.` ссылки, включая dynamic SQL, к новым
случайным `w11_*` схемам. Настоящие raw/core/mart не загружаются и не меняются.
Используются существующие SQL-стадии 05/10/20/30/40/50/90; исходный raw DDL тоже
перенаправляется в test schema. Каждая попытка откатывается к savepoint; в конце
откатываются все test schemas и проверяется их отсутствие. Работа идёт только
в выделенной тестовой БД; `marketplace`, `postgres`, templates отвергаются.

Сценарии: 2 items × 3 payments × 2 reviews (12 строк наивного join, правильные
независимые суммы); missing child/all NULL/known zero/partial/one-sided payments;
точное сохранение 1.234; reject NaN; неверный integer/NULL key; duplicate item key;
dangling FK; новый статус warning; review payload conflict warning с сохранением
двух вариантов; duplicate review-order pair; пропущенный день; +10/−10 на разных
заказах при неизменной общей сумме; потерянный review text; удалённая/подменённая
позиция; duplicate core multiplicity. Базовый сценарий также проверяет NULL late,
same-day day/timestamp и разные min/max item deadlines под разными именами.

Ожидаемая ошибка принимается только при совпадении SQLSTATE **и** нужного текста
диагностики. Любая другая ошибка, отсутствие ожидаемой ошибки или пропуск
warning — неуспех; полный error text сохраняется в JSON отчёте.

После разрешённого появления стенда, с уже настроенным `RWB_TEST_DSN`:

```bash
python3 scripts/verify-model.py --run-fixtures > /tmp/rwb-w11-fixtures.json
```

DSN/пароль не передаются в argv, отчёт или Git. Наличие runner/fixture не означает
их PASS. Ограничение ресурсов Mac остаётся в силе.

## Clean build, rebuild, late rollback · pending

Для полного протокола нужна отдельная БД с загруженным организаторским raw и
пустыми core/mart; загрузка raw — отдельная операция, не часть build. Сначала
проверяется доступность разрешённого стенда по [build runbook](build-runbook.md).
На этом Mac новый тяжёлый запуск требует успешного `/Users/a/bin/dev-job preflight`;
код 78 не обходится. Подготовленный протокол не создаёт БД/контейнер/зависимости.

Используйте libpq `PGSERVICE` либо `PGHOST/PGPORT/PGDATABASE/PGUSER` и существующий
безопасный способ аутентификации. Приостановите raw reload/DDL на всё время
протокола. Операторский флаг — подтверждение режима, не автоматическая проверка
отсутствия writers. Никакая изоляция snapshot сама по себе не защищает от TRUNCATE.

```bash
RWB_RAW_RELOAD_PAUSED=1 bash tests/model/validate-lifecycle.sh
```

Скрипт откажется от рабочей `marketplace` и непустой модели, сверит CSV↔raw,
выполнит build с нуля, повторит его и сравнит content/multiplicity fingerprints
всех core/mart relations и определения объектов (игнорируя только timestamp
выполнения checks). Затем [rollback.sql](../tests/model/rollback.sql) выполнит
весь build и намеренно выбросит `W11_INJECTED_LATE_FAILURE_AFTER_ALL_CHECKS`.
Принимается только psql exit 3 с этим маркером; после rollback fingerprints
должны совпасть с последним успешным build, включая raw и определения объектов.
После успешного CSV↔raw binding скрипт сверяет восемь pin-хешей с baseline и
байты audit manifest, затем сам устанавливает точный token для последующего
`control`. До binding этот token автоматически не выдаётся. Далее выполняются
отдельные `check` и baseline `control`, повторяется manifest.

Скрипт сохраняет логи, manifest и небольшие fingerprints в выведенный evidence
directory, не удаляет их и не выгружает полные данные. Тестовая БД после двух
успешных build содержит модель; отрицательный build не должен изменить её.
Совпадение fingerprints — дополнительный контроль content/DDL, а не замена
row-level assertions или доказательство concurrent-loader safety.

Остаётся отдельно проверить на изолированном стенде: права и внешние зависимости,
оба порядка гонки с loader DROP/CREATE и `--skip-ddl`, таймауты и исход commit
при потере соединения. После connection loss нельзя принимать rollback по exit
или делать слепой retry. Новый SQL-вопрос и бизнес-ответы требуют фактического
выполнения по core/mart; эти результаты здесь не заявлены.
