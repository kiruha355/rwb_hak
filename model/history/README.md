# Источник истории и выпуски модели

`history.*` — сохраняемый SQL-источник. `core.*` / `mart.*` — пересоздаваемые
проекции одного явно выбранного выпуска. Здесь нет HTTP, маршрутизации отчётов,
публикации официального пересмотра, новых ролей или внешнего хранилища.

## Сборка

Первый `bash scripts/build-model.sh build` в разрешённой фазе с остановленной
загрузкой raw атомарно создаёт `original-v1`: product baseline, taxonomy, исходную
популяцию и bindings всех позиций. `baseline_snapshot.business_valid_from` всегда
NULL. `captured_at` — фактическое время фиксации, сохраняемое при rebuild.
Привязка baseline означает `snapshot_at_bootstrap`, а не Olist as-of.

Обычная повторная сборка выбирает неизменяемый `history.initial_release`, даже
после добавления events/других releases. Для другого выпуска оператор явно задаёт
`RWB_REPORT_RELEASE=R1` при вызове того же wrapper. Значение передаётся безопасно
через quoted psql variable. `core.model_release` показывает, что материализовано.
`answers` читает текущую материализацию, а не переключает выпуск.

Перед DROP сравниваются все восемь raw business payloads с закреплённым release:
SHA256 JSONB строки + её multiplicity, в стабильном порядке. `_loaded_at` и
`_source_file` — техническая загрузочная метаинформация, не бизнес-данные; они
исключены из business digest. Типизированные core↔raw проверки остаются отдельно.
Изменение/добавление raw не запускает автоматический rebootstrap. Старый выпуск
требует своей raw generation в отдельной БД либо восстановления её из архива.

## Приём событий

Интерфейс — доверенный SQL в управляемой транзакции. Пример полностью
синтетический; не утверждает наличие такого изменения в Olist:

```sql
BEGIN;
SELECT history.append_event(
    'catalog/E1', 'P', 'S1', 'set', 'pt:B',
    timestamp '2018-01-10', NULL, 'source_naive_purchase_v1', NULL,
    '{"source":"synthetic-example","reason":"category assignment"}'::jsonb);
COMMIT;
```

`event_id` — стабильная identity источника; provenance обязателен. Точный retry
возвращает прежний ID, другой payload того же ID вызывает ошибку. Receipt
`recorded_at` генерируется один раз БД. SHA256 payload также задаёт стабильную
version identity `e:<hash>`; baseline использует `b:<hash(snapshot,product)>`.

NULL seller — product scope, конкретный seller — override. Выбор: последний
применимый seller event; при `unset_override` — product event; затем baseline.
`set` с `category_key='unknown'` остаётся неизвестной категорией, не снимает override.
Product events не перекрывают активный seller override. Возврат к той же категории
имеет другую version identity, если источник зарегистрировал новое событие.

Границы включительны: новая версия действует с `from`; до следующей границы
получается интервал `[from,next_from)`. Baseline остаётся отдельным fallback с
неизвестным business start. Фиктивный `-infinity` не сохраняется.

Допустимы либо `business_valid_from`, либо явный `policy_apply_from` для observed
события. `source_naive_purchase_v1` — утверждение источника о сопоставимости его
naive boundary с purchase clock. Это не выбор timezone для Olist и не перевод UTC
receipt в business time. При неизвестных обоих временах NULL/NULL/NULL сохраняет
observation как evidence и не включает его в автоматическое разрешение. Время
наблюдения и дополнительные source revision/authority references можно сохранять
в provenance. Реальные полномочия SQL helper не проверяет.

Correction — новый event с `supersedes_event_id`. Target уже должен существовать,
product/seller scope совпадает, correction fork запрещён UNIQUE. Разрешение сначала
ограничивает события точным event set выпуска, затем исключает superseded. Нельзя
забыть target correction или выбрать missing event. Два активных события одного
scope на одной boundary блокируют выпуск; случайный UUID не определяет победителя.

Все helper writers и build используют один try-advisory-xact lock. При конфликте,
serialization failure или неопределённом исходе COMMIT требуется readback и явный
retry оператора. Автоматических повторов нет. Прямые SQL writers вне этого
протокола не сериализуются им.

## Создание выпуска

```sql
BEGIN;
SELECT history.create_release(
    'R1', 'extension', 'original-v1', ARRAY['catalog/E1'],
    timestamp '2018-01-13');
COMMIT;
```

Создание выпуска только сохраняет manifest/bindings; оно не переключает модель
или официальный отчёт. Для пробной материализации в нужной изолированной БД:

```bash
RWB_REPORT_RELEASE=R1 bash scripts/build-model.sh build
```

`extension` копирует все прежние bindings, включая старые версии superseded events.
Все parent raw rows должны остаться byte-equivalent по business payload, с прежней
multiplicity; существующая taxonomy тоже сохраняется. Новые source products
получают новый baseline snapshot с unknown business time, прежние bindings
сохраняют старый baseline ID. Появление нового translation label для старого
category member требует restatement. `closed_before` не может двигаться назад;
новые order/item/payment/review строки ранее parent boundary, включая неизвестную
purchase date, запрещены. Boundary задаёт первый открытый момент, не системные часы.
Начальная boundary — максимум purchase snapshot + 1 microsecond (это граница
закрытой популяции отчёта, не дата начала категории).

```sql
BEGIN;
SELECT history.append_event(
    'catalog/E2', 'P', 'S1', 'set', 'pt:B',
    timestamp '2018-01-04', NULL, 'source_naive_purchase_v1', 'catalog/E1',
    '{"source":"synthetic-example","reason":"late correction"}'::jsonb);
SELECT history.create_release(
    'R1-restated', 'restatement', 'R1', ARRAY['catalog/E1','catalog/E2'],
    timestamp '2018-01-13');
COMMIT;
```

`restatement` заново разрешает все текущие items и явно допускает поздние строки
и исправления источника. Никакого human approval этим SQL не объявляется.
Прежние releases/bindings/result digests остаются доступными. Exact create retry
требует совпадения kind, parent, event set, boundary и raw digest; конфликт — ошибка.
Изменения source/order statuses/prices также требуют новой raw generation/release.

Headers вставляются последними: child rows + header — одна транзакция, после чего
manifest запечатан. UPDATE/DELETE/TRUNCATE guarded triggers запрещены; добавление
bindings/taxonomy/source rows к существующему release тоже. Неудачная транзакция
не оставляет candidate release. Уже committed event после failed build сохраняется.
Бизнес-откат — compensating event + новый release, не удаление журнала.

## Восстановление

Сохранять нужно bytes, не только hashes. Обязательная резервная копия — схема
`history` целиком (включая baseline, events, release manifests, bindings, labels,
result digests) плюс точная raw generation/исходные CSV каждого нужного выпуска.
Например, для согласованного SQL-снимка текущей generation используются установленные
`pg_dump --schema=raw --schema=history --no-owner --no-acl` с явными libpq параметрами
оператора. Не вызывать его на рабочей БД без соответствующей задачи.

Dump `history` сам по себе сохраняет источник категорий; без исходного raw он не
восстановит суммы/адреса/статусы. В пустой изолированной БД: restore raw+history,
затем build с нужным `RWB_REPORT_RELEASE`. `core/mart` восстанавливаются без их dump.
Именно этот путь реально проверяет synthetic runner; retained SQL dump в evidence
содержит исключительно синтетические строки. Архив реального Olist здесь не создавался.

Перед восстановлением projections проверяются baseline/event content hashes,
raw population/payload, binding hash и taxonomy hash. После общих core invariants
проверяются version source/scope и суммы historical mart. Первый успешный build
закрепляет SHA256 строк всех 13 Q1–Q10 answer relations; следующий build того же
release должен дать тот же result manifest. Изменение metric policy требует
нового release, даже если raw/bindings не менялись.

Одна БД содержит одну текущую материализацию `core/mart`, а не все версии сразу.
Роутинг старых отчётов, хранение архивов вне БД, backup schedule, разграничение ролей
и официальная публикация пересмотра остаются задачами интеграции. Triggers и
REVOKE PUBLIC не ограничивают owner/superuser и не являются production authority.
Canonical JSONB hashing в этой реализации привязан к PG16; миграцию major version
и крупные объёмы нужно проверять отдельно.

## Проверки

Из корня выделенного checkout:

```bash
python3 tests/model/history/verify-small-pg16.py /tmp/rwb-history-evidence-new
```

Runner требует уже установленные PG16 и psycopg, создаёт свой cluster в `/tmp`,
Unix socket, listen_addresses пуст, shared_buffers=16MB, max_connections=5,
max_parallel_workers=0. Он не использует существующие endpoints, Docker, Olist CSV
или installations. Свои процессы останавливает, runtime удаляет; evidence сохраняет.

Общие invariants — `model/90_checks.sql` и `history/04_checks.sql`. Конкретные
синтетические regression values — только runner/assert-base. Публичные Q6–Q10
проверяются исходными 16-order assertions с адаптацией только stage loader в памяти;
исходный файл assertions не меняется. Полный Olist/control.sql не запускался.
