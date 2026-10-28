# Детальная модель Capibara

W-08 · repository `kiruha355/rwb_hak` · input main
`1939068295d7203a15cbb0a1ab5d407caca90f58` · research
`72c1fb6ffe43e95b2ba539dc1b396374f4bfde3a`.
Исполнитель: Codex / Sol. Это реализация разрешённого рабочего направления;
форма constellation и спорные определения метрик не объявляются человеческим approval.
**PostgreSQL runtime, загрузка core и контрольные ответы пока не проверены.**

Точный интерфейс для build/mart/check workers — [CONTRACT.md](../model/CONTRACT.md).
DDL/загрузка измерений — [10_dims.sql](../model/10_dims.sql), фактов —
[20_facts.sql](../model/20_facts.sql). Все восемь источников из
[raw DDL](../scripts/init/02_raw_ddl.sql) только читаются. Сборщик владеет транзакцией,
согласованностью поколения raw, очисткой принадлежащих ему объектов и самопроверками.
Фрагменты W-08 не выполняют reset/COMMIT и не являются самостоятельным идемпотентным build.

## Гранулярность и связи

| Таблица core | Одна строка и ключ | Связи / назначение |
|---|---|---|
| `dim_date` | День, PK `date_day` | Все восемь timestamp-ролей через `::date`; непрерывный календарь, минимум сентябрь 2016 — август 2018 |
| `dim_order_status` | Значение статуса, PK `order_status` | Одна точка правила `is_revenue`; known domain плюс наблюдаемые новые статусы |
| `dim_customer` | Покупатель, PK `customer_unique_id` | Адрес не выбирается из нескольких customer contexts |
| `dim_customer_context` | Исходный customer context, PK `customer_id` | FK на покупателя; UNIQUE `(customer_id, customer_unique_id)` для order FK; все строки customers независимо от заказов |
| `dim_seller` | Продавец, PK `seller_id` | Исходная география без угадывания исправленного города |
| `dim_category` | Категория PT или unknown, PK `category_key`; UNIQUE `name_pt` | Домен products ∪ translation; перевод необязателен |
| `dim_product` | Товар, PK `product_id` | Обязательный FK `category_key` |
| `fact_order` | Заказ, PK `order_id` | Обязательные FK buyer/status и composite customer context; адрес этого заказа |
| `fact_order_item` | Единица из исходной строки, PK `(order_id, order_item_id)` | Обязательные FK order/product/seller |
| `fact_payment` | Исходная строка платежа, PK `(order_id, payment_sequential)` | Обязательный FK order |
| `fact_review` | Связь отзыв–заказ со своим payload, PK `(review_id, order_id)` | Обязательный FK order; `review_id` сам по себе не уникален |

`fact_order` загружается из всех orders через LEFT JOIN к уникальному customer context.
Отсутствие context вызывает NOT NULL/FK error вместо потери заказа. Ни один child не
участвует в загрузке заказа: 0/1/много items/payments/reviews не меняют grain orders.
`dim_customer_context` дополняет шесть основных измерений, чтобы не терять исходного
покупателя/адрес при отсутствии заказа. В текущем снимке customer_id выдан на заказ;
проверка этого наблюдения не превращается в запрет будущему customer_id иметь два заказа.

## Mapping всех 47 бизнес-полей восьми источников

`text` означает точное сохранение значения, включая регистр, пробелы и пустой текст.
`integer`/`numeric`/`timestamp` означают описанную ниже проверку и приведение, без
подстановки NULL и без округления денежной суммы. Метаданные `_source_file` и
`_loaded_at` каждого источника остаются в raw: это отдельные 16 технических полей,
не потерянные бизнес-атрибуты; связь с build manifest относится к сборщику.

| Источник raw | Поле | Назначение core / преобразование |
|---|---|---|
| `orders` | `order_id` | `fact_order.order_id`, text PK |
| `orders` | `customer_id` | `fact_order.customer_id`, text FK к исходному контексту |
| `orders` | `order_status` | `fact_order.order_status` и домен `dim_order_status.order_status`, text |
| `orders` | `order_purchase_timestamp` | `fact_order.order_purchase_timestamp`, timestamp; дата также в календаре |
| `orders` | `order_approved_at` | `fact_order.order_approved_at`, timestamp; дата также в календаре |
| `orders` | `order_delivered_carrier_date` | `fact_order.order_delivered_carrier_date`, timestamp; дата также в календаре |
| `orders` | `order_delivered_customer_date` | `fact_order.order_delivered_customer_date`, timestamp; дата также в календаре |
| `orders` | `order_estimated_delivery_date` | `fact_order.order_estimated_delivery_date`, timestamp; дата также в календаре |
| `order_items` | `order_id` | `fact_order_item.order_id`, text FK и часть PK |
| `order_items` | `order_item_id` | `fact_order_item.order_item_id`, integer, часть PK внутри заказа |
| `order_items` | `product_id` | `fact_order_item.product_id`, text FK |
| `order_items` | `seller_id` | `fact_order_item.seller_id`, text FK |
| `order_items` | `shipping_limit_date` | **Alias** `fact_order_item.shipping_limit_at`, timestamp; дата также в календаре |
| `order_items` | `price` | `fact_order_item.price`, numeric |
| `order_items` | `freight_value` | `fact_order_item.freight_value`, numeric |
| `order_payments` | `order_id` | `fact_payment.order_id`, text FK и часть PK |
| `order_payments` | `payment_sequential` | `fact_payment.payment_sequential`, integer, часть PK |
| `order_payments` | `payment_type` | `fact_payment.payment_type`, text |
| `order_payments` | `payment_installments` | `fact_payment.payment_installments`, integer |
| `order_payments` | `payment_value` | `fact_payment.payment_value`, numeric |
| `order_reviews` | `review_id` | `fact_review.review_id`, text, часть PK пары |
| `order_reviews` | `order_id` | `fact_review.order_id`, text FK и часть PK пары |
| `order_reviews` | `review_score` | `fact_review.review_score`, integer |
| `order_reviews` | `review_comment_title` | `fact_review.review_comment_title`, полный text |
| `order_reviews` | `review_comment_message` | `fact_review.review_comment_message`, полный text |
| `order_reviews` | `review_creation_date` | `fact_review.review_creation_date`, timestamp, не date; дата также в календаре |
| `order_reviews` | `review_answer_timestamp` | `fact_review.review_answer_timestamp`, timestamp; дата также в календаре |
| `products` | `product_id` | `dim_product.product_id`, text PK |
| `products` | `product_category_name` | `dim_product.category_key` → `dim_category.name_pt`, точное имя или unknown при NULL |
| `products` | `product_name_lenght` | `dim_product.product_name_lenght`, integer; исходная опечатка сохранена |
| `products` | `product_description_lenght` | `dim_product.product_description_lenght`, integer; исходная опечатка сохранена |
| `products` | `product_photos_qty` | `dim_product.product_photos_qty`, integer |
| `products` | `product_weight_g` | `dim_product.product_weight_g`, numeric, граммы |
| `products` | `product_length_cm` | `dim_product.product_length_cm`, numeric, сантиметры |
| `products` | `product_height_cm` | `dim_product.product_height_cm`, numeric, сантиметры |
| `products` | `product_width_cm` | `dim_product.product_width_cm`, numeric, сантиметры |
| `sellers` | `seller_id` | `dim_seller.seller_id`, text PK |
| `sellers` | `seller_zip_code_prefix` | `dim_seller.seller_zip_code_prefix`, исходный text + отдельный derived `_validated` |
| `sellers` | `seller_city` | `dim_seller.seller_city`, text |
| `sellers` | `seller_state` | `dim_seller.seller_state`, text |
| `customers` | `customer_id` | `dim_customer_context.customer_id`, text PK; lookup для `fact_order` |
| `customers` | `customer_unique_id` | `dim_customer.customer_unique_id`, `dim_customer_context.customer_unique_id`, `fact_order.customer_unique_id`, text |
| `customers` | `customer_zip_code_prefix` | `dim_customer_context` и `fact_order.customer_zip_code_prefix`, исходный text + отдельный `_validated` |
| `customers` | `customer_city` | `dim_customer_context` и `fact_order.customer_city`, text |
| `customers` | `customer_state` | `dim_customer_context` и `fact_order.customer_state`, text |
| `product_category_translation` | `product_category_name` | **Alias** `dim_category.name_pt`, text; ключ `category_key = 'pt:' || name_pt` |
| `product_category_translation` | `product_category_name_english` | **Alias** `dim_category.name_en`, text, nullable |

## Сохранность, типы и ограничения

Покупатель — `customer_unique_id`; `customer_id` сохраняет исходную связь и адресный
контекст. На buyer dimension намеренно нет «последнего адреса», first/last timestamp,
демографии или истории, которых источник не сообщает. Географические координаты
отсутствуют в восьми источниках и не создаются из ZIP.

Исходный ZIP остаётся source-named text. Колонка `*_zip_code_prefix_validated`
вычисляется только для `^[0-9]{1,5}$` через `lpad(value, 5, '0')`: `1234 → 01234`,
`01234 → 01234`; NULL, `123456`, `12x4`, ` 1234` дают derived NULL. Исходник при
этом сохраняется полностью. CHECK использует `IS NOT DISTINCT FROM`, поэтому
проверяет и точное NULL-поведение, а не пропускает его через SQL UNKNOWN.

Все натуральные ключи имеют PRIMARY KEY; обязательные идентификаторы NOT NULL;
пустые/состоящие из обычных пробелов текстовые ключи блокируются до вставки.
Адресные поля, даты и измеренные значения nullable. Нет hard CHECK на положительность
цены/веса, score 1–5, installments > 0 или хронологию: необычный источник сохраняется,
а качество отражается отдельными предупреждениями. FK запрещает потерянные связи;
недостающий справочник не подменяется придуманным продавцом или покупателем.

Координированный `05_typecheck.sql` выполняется до W-08 фрагментов. Integer имеет
строгую целую запись `^[+-]?[0-9]+$`, decimal numeric —
`^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)$`; неверный формат, overflow, NaN и Infinity
блокируются. Деньги и размеры имеют **numeric без `(p,s)`**: `1.234` остаётся
`1.234`, не `1.23`; наблюдаемый нулевой платёж и NULL различны. Формат с exponent
или пробелами требует явной новой политики, а не неявного преобразования.
Типизированный round-trip сравнивает значения: лексические варианты `001` и `1`
после integer cast совпадают; исходная запись доступна в неизменяемом raw.

Все timestamps — `timestamp without time zone`, строго `YYYY-MM-DD HH:MM:SS`.
Источник не сообщает timezone; сдвиг в UTC не угадывается. Offset, дробные секунды,
`24:00:00` и leap-second `:60` не нормализуются молча: W-08 проверяет форму до cast;
невозможная дата/выход диапазона вызывает ошибку приведения. NULL сохраняется.
`review_creation_date` хранит timestamp, хотя в названии есть `date`.

Категория с исходным NULL получает ключ `'unknown'` и `name_pt/name_en = NULL`.
Любое известное PT-имя, включая исходный пустой text, получает
отдельный `'pt:' || name_pt`: sentinel не сталкивается с реальным именем `unknown`.
Известная PT-категория без translation остаётся известной (`is_unknown=false`,
`is_translated=false`, `name_en=NULL`). English fallback не выдумывается.
Домен включает неиспользованные translation rows; их имя и перевод сохраняются.
`has_translation_row` сохраняет членство в исходном справочнике отдельно от
`is_translated`, даже если у существующей translation row English равен NULL.
По этому флагу можно восстановить все строки translation, а не угадывать их
существование по заполненности перевода.
Повтор ключа translation блокирует загрузку, а не выбирает первый вариант.

`fact_review` не выбирает один текст на `review_id`. Разные order pairs с одним
review_id и разными score/title/message/date сохраняются каждая со своим payload.
Дубли одной естественной пары, даже идентичные, вызывают PK error: нет скрытого
DISTINCT/ROW_NUMBER/latest. Raw остаётся доступным для разбора; если новый источник
допускает несколько payload одной пары, нужен явный новый ключ/version contract.
Представление review entity и веса ID/pair/order остаются отдельными именованными
вариантами в mart. `latest` не доказывает «актуальное мнение».

Календарь строится по минимуму/максимуму всех 5 order timestamps, item deadline и
2 review timestamps, с включением минимум `2016-09-01–2018-08-31`. Число дней
генерируется целыми смещениями даты, без timezone/DST зависимости. Даже при пустом
raw минимум окна сохранится. Q1 выбирает **24 месяца явным фильтром**, а не весь
календарь; месяц без заказов присутствует. Максимум event date не объявляется as-of.

## Индексы и границы метрик

PRIMARY/UNIQUE дают индексы естественных ключей. Дополнительно созданы индексы
date month, context buyer, product category; order buyer/context, purchase и
status+purchase; item product и seller+order; payment type; review order.
PK item/payment начинается с order_id и покрывает их order FK, а review PK
начинается с review_id, поэтому review order индекс нужен отдельно. Это небольшой
набор для связей и типовых срезов, без утверждений о latency или нагрузочном benchmark.

`dim_order_status.is_revenue` равен true только у `delivered` согласно определению
выручки задания. Новый статус сохраняется как отдельный член с false и должен
появиться в предупреждениях; отсутствие такого предупреждения не означает approval.
Факт не хранит вторую расходящуюся копию revenue flag. Delivered не доказывает выкуп,
отсутствие возврата или банковское зачисление.

В core нет order sums/review averages/late flags, которые навязали бы спорное правило.
Mart независимо агрегирует items/payments/reviews до нужного grain и только потом
соединяет их с orders. `sum(price)` и `sum(price+freight_value)` имеют разные компоненты;
NULL-компонент нельзя спрятать под coalesce. Должны быть видны completeness и
both/items_only/payments_only/neither. Counts/windows, review weights и late rules
сохраняются с разными именами, пока человек/организаторы не выбрали конкретный смысл.

## Проверки и предел доказательства

В W-08 выполняются только малые static/offline проверки; их фактические результаты
добавляются ниже. База не запускалась, CSV не загружались заново, DDL не выполнялся
на liveDB. Ключи, constraints, PostgreSQL evaluation, raw→core equality и answers
не получают PASS по одному разбору синтаксиса.

Воспроизводимая static-проверка требует только Python 3 и временный wheel
`pglast==6.17` (встроенный parser PostgreSQL 16.1). Скрипт ниже запускается из корня
репозитория; он не подключается к БД и ничего не записывает. Проверяются SQL и
PL/pgSQL syntax, создание/загрузка только core, совместимость FK с PK/UNIQUE и
типами, наличие всех target columns, unconstrained numeric и полнота mapping.

<!-- W08_STATIC_CHECK -->
```python
from pathlib import Path
import re
import pglast
from pglast import parse_sql, parse_plpgsql, get_postgresql_version

assert get_postgresql_version()[0] == 16
tables, keys, fks, insert_count, do_count = {}, {}, [], 0, 0
contract = Path('model/CONTRACT.md').read_text()
for filename in ('10_dims.sql', '20_facts.sql'):
    sql = Path('model', filename).read_text()
    statements = parse_sql(sql)
    for raw_stmt in statements:
        stmt = raw_stmt.stmt
        kind = type(stmt).__name__
        assert kind in {'DoStmt', 'CreateStmt', 'InsertStmt', 'IndexStmt', 'CommentStmt'}, kind
        if kind == 'DoStmt':
            body = sql[raw_stmt.stmt_location:raw_stmt.stmt_location + raw_stmt.stmt_len]
            parse_plpgsql(body + ';')
            assert not re.search(r'\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|COMMIT)\b', body, re.I)
            do_count += 1
        elif kind == 'CreateStmt':
            assert stmt.relation.schemaname == 'core'
            name = stmt.relation.relname
            assert name not in tables
            cols = {c.colname: c for c in stmt.tableElts if type(c).__name__ == 'ColumnDef'}
            tables[name], keys[name] = cols, set()
            assert all(re.search(r'\b' + re.escape(c) + r'\b', contract) for c in cols)
            constraints = [(c, None) for c in stmt.tableElts if type(c).__name__ == 'Constraint']
            constraints += [(c, col.colname) for col in cols.values() for c in (col.constraints or ())]
            for c, inline_column in constraints:
                rule = c.contype.name
                if rule in {'CONSTR_PRIMARY', 'CONSTR_UNIQUE'}:
                    local = (inline_column,) if inline_column else tuple(x.sval for x in c.keys)
                    assert all(col in cols for col in local)
                    keys[name].add(local)
                elif rule == 'CONSTR_FOREIGN':
                    local = (inline_column,) if inline_column else tuple(x.sval for x in c.fk_attrs)
                    assert c.pktable.schemaname == 'core'
                    fks.append((name, local, c.pktable.relname, tuple(x.sval for x in c.pk_attrs)))
            for col in cols.values():
                if col.typeName.names[-1].sval == 'numeric':
                    assert not col.typeName.typmods, 'numeric scale could round source'
        elif kind == 'InsertStmt':
            assert stmt.relation.schemaname == 'core'
            name = stmt.relation.relname
            target = [c.name for c in stmt.cols]
            assert target == list(tables[name]), (name, target)
            query = stmt.selectStmt
            width = len(query.targetList) if query.targetList else len(query.valuesLists[0])
            assert len(target) == width
            if name.startswith('fact_'):
                assert not query.distinctClause and not query.groupClause
                assert not query.whereClause and not query.limitCount
                source = query.fromClause[0]
                if name == 'fact_order':
                    assert source.jointype.name == 'JOIN_LEFT'
                    assert (source.larg.schemaname, source.larg.relname) == ('raw', 'orders')
                    assert (source.rarg.schemaname, source.rarg.relname) == ('core', 'dim_customer_context')
                else:
                    expected = {'fact_order_item': 'order_items', 'fact_payment': 'order_payments',
                                'fact_review': 'order_reviews'}[name]
                    assert len(query.fromClause) == 1
                    assert (source.schemaname, source.relname) == ('raw', expected)
            insert_count += 1
        elif kind == 'IndexStmt':
            assert stmt.relation.schemaname == 'core'
    print(filename, len(statements), 'statements: PARSE_OK')
for name, local, referenced, remote in fks:
    assert referenced in tables and remote in keys[referenced]
    assert len(local) == len(remote)
    for a, b in zip(local, remote):
        assert tables[name][a].typeName.names[-1].sval == tables[referenced][b].typeName.names[-1].sval
source_fields = set()
for raw_stmt in parse_sql(Path('scripts/init/02_raw_ddl.sql').read_text()):
    stmt = raw_stmt.stmt
    if type(stmt).__name__ == 'CreateStmt':
        source_fields |= {(stmt.relation.relname, c.colname) for c in stmt.tableElts
                          if type(c).__name__ == 'ColumnDef' and not c.colname.startswith('_')}
mapping = re.findall(r'^\| `(\w+)` \| `(\w+)` \|', Path('docs/model.md').read_text(), re.M)
assert len(mapping) == len(set(mapping)) == len(source_fields) == 47
assert set(mapping) == source_fields
dim_sql = Path('model/10_dims.sql').read_text()
date_cte = dim_sql.split('WITH event_dates AS (', 1)[1].split('), bounds AS (', 1)[0]
for role in ('order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date',
             'order_delivered_customer_date', 'order_estimated_delivery_date',
             'shipping_limit_date', 'review_creation_date', 'review_answer_timestamp'):
    assert role in date_cte
assert "DATE '2016-09-01'" in dim_sql and "DATE '2018-08-31'" in dim_sql
assert 'generate_series(0, b.last_day - b.first_day)' in dim_sql
print('PostgreSQL parser:', get_postgresql_version(), 'pglast:', pglast.__version__)
print('tables:', len(tables), 'FK:', len(fks), 'INSERT:', insert_count,
      'PL/pgSQL blocks:', do_count, 'mapped fields:', len(mapping), 'STATIC_OK')
```
<!-- /W08_STATIC_CHECK -->

Фактически выполнено 2026-10-28: извлечение этого Python-блока из документа и запуск
в отдельном временном venv с `pglast==6.17`, exit 0:

```text
10_dims.sql 40 statements: PARSE_OK
20_facts.sql 39 statements: PARSE_OK
PostgreSQL parser: (16, 1) pglast: v6.17
tables: 11 FK: 10 INSERT: 12 PL/pgSQL blocks: 3 mapped fields: 47 STATIC_OK
```

Точная команда запуска после подготовки parser environment (значение
`PARSER_PYTHON` — путь к Python с указанным wheel):

```sh
"$PARSER_PYTHON" - <<'PY'
from pathlib import Path
text = Path('docs/model.md').read_text()
code = text.split('<!-- W08_STATIC_CHECK -->', 1)[1].split('```python\n', 1)[1].split('\n```', 1)[0]
exec(compile(code, 'docs/model.md:W08_STATIC_CHECK', 'exec'))
PY
```

Дополнительно static-дерево подтверждает отсутствие фильтра/агрегации/dedup на
всех четырёх fact INSERT, единственный LEFT JOIN orders к context и охват всех
восьми date roles. Это проверка структуры, не фактической сохранности loaded rows.
Временный parser environment не является частью сдаваемой модели или зависимостью build.

Runtime acceptance для владельца стенда: чистый build и повтор, поздняя ошибка с
полным rollback, counts/key+value multisets восьми источников после указанных cast,
FK/NULL и отдельные денежные totals, все review payload, customers без заказов,
translation без products, неизвестные/непереведённые категории, все calendar roles
и проверка отсутствия gaps. Негативные случаи: duplicate pair, конфликт одного
review_id на разных заказах (должен сохраниться), orphan, NULL/пустой key, fractional
integer, numeric `1.234`/NaN/overflow, timestamp offset/invalid date/24:00 и chronology
anomaly (должна остаться warning), malformed ZIP и source text с пробелами.

Следующий runtime шаг выполняется сборщиком **после** снятия resource/daemon блокеров
и согласования изолированного стенда; это не разрешение W-08 запустить live DDL.
После настройки endpoint/auth этого стенда и выполнения протокола паузы raw
из [build runbook](build-runbook.md), точная команда владельца сборки:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host bash scripts/build-model.sh build
```

Переменная обозначает подтверждённую паузу, не останавливает loader сама.

## Источники и вклад ИИ

SQL и этот mapping написаны агентом по raw DDL, implementation brief и точным
published input refs; сторонний SQL не копировался. Основания: synthesis §7.1 и
research S02–S11. Рабочие технические решения остаются изменяемыми; static review
агента и совпадение baseline не заменяют независимую runtime-проверку.
