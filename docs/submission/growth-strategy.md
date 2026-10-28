# Стратегия развития модели

**Рабочее предложение:** сохранить детальный PostgreSQL-core как проверяемую основу, измерить реальную нагрузку, затем менять физическую реализацию и вводить инкременты. Число строк само по себе не даёт порога миграции. На наших 550 759 исходных records производительность PostgreSQL ещё не измерялась; говорить, что он уже выдержал SLA, нельзя.

## 1. Нагрузка и SLA до выбора стека

Ниже — **сценарий измерения и предложенные цели**, не согласованный бизнес-SLA и не результат benchmark. Машина стенда, RAM/CPU/диск, версия, конфигурация, input manifest и SQL одинаковы для сравнения вариантов. Тяжёлые прогоны на текущем Mac запрещены guard.

| Workload | Что воспроизводить | Предложенная цель для обсуждения | Что измерять |
|---|---|---|---|
| Короткий drill-through | Заказ со всеми независимыми children, выборочные buyer/seller | P95 ≤1 с, 5 одновременных читателей | End-to-end latency, CPU, reads, количество возвращённых строк |
| Дашборд | Q1–Q5 + delivery/quality, типичные фильтры и worst case весь период | P95 ≤3 с при 10 читателях; неизвестное/ошибка видимы | P50/P95/P99, throughput, temp spill, cache, query plans |
| Обновление модели | Full build+checks; затем те же входы incremental+checks | Вписаться в согласованное окно; для daily-сценария кандидат ≤30 мин | Wall time, lock wait, WAL/IO, peak memory, lag, время checks |
| Свежесть | Изменение источника→видимость в проверенном mart | Кандидат daily ≤24 ч; оперативный ≤15 мин требует другого источника | Source event lag и load lag раздельно, потери/дубли/ошибки |
| Восстановление | Restore backup + replay + checks + публикация | Кандидат RPO ≤24 ч и RTO ≤2 ч для daily; требует подтверждения владельца | Возраст последнего события, полное время восстановления и паритет |

Сначала baseline текущего снимка. Затем на разрешённом изолированном стенде — 10× и 100× данных с сохранением распределений, skew, длины отзывов и кратностей children. Это **точки эксперимента**, не утверждение достаточности PostgreSQL до такого объёма. Каждый объём считать как rows + bytes + indexes + WAL + temp + backup. Warm/cold cache, concurrency и mixed read/build задаются отдельно; быстрый один SELECT не равен скорости дашборда.

Кандидат триггера пересмотра: повторяемое нарушение согласованного P95/freshness/recovery budget на целевом workload после измеренных оптимизаций, либо TCO альтернативы существенно лучше при том же качестве. Частоту и допустимый запас согласовать; выдуманного «предела 5/50 млн строк» здесь нет.

## 2. Что, вероятно, упрётся первым

Это гипотезы для профилирования: full scans/join/aggregate по деталям и текстам; повторная сборка всего снимка; дисковый IO/temp при конкуренции; история/индексы/backup; lock contention при загрузке. Реальный порядок определяется `EXPLAIN (ANALYZE, BUFFERS)` на разрешённом стенде и end-to-end метриками, не числом таблиц.

Порядок малых обратимых улучшений:

1. Исправить fanout и лишнюю работу, сохранить общий grain; проверить планы и статистику. Это одновременно корректность и цена запроса.
2. Добавлять индексы под измеренные filters/joins. Учитывать стоимость записи, размер, vacuum и build; не добавлять все индексы заранее.
3. Повторяющиеся дорогие расчёты вынести в проверяемые aggregates/materialized views с договором freshness и обновления. Детали остаются доступными для новых вопросов.
4. Рассмотреть partitioning по реальному pruning/retention workload. Не делать месячные partition автоматически. В PostgreSQL 16 unique/primary key partitioned table должен включать все partition keys: `(order_id,date)` сам по себе не доказывает глобальную уникальность `order_id`.

Документированное ограничение и компромиссы: [PostgreSQL 16 partitioning](https://www.postgresql.org/docs/16/ddl-partitioning.html#DDL-PARTITIONING-DECLARATIVE-LIMITATIONS), прочитано 2026-10-28. Это свойство технологии, не benchmark нашего проекта.

## 3. История требует новых свидетельств

| Что хотим знать | Нужный источник и grain | Историчность и правило |
|---|---|---|
| Каким был товар/продавец в момент заказа | Versioned product/seller changes с stable ID, effective_at, source_updated_at и sequence | SCD2 для атрибутов с бизнес-смыслом; `valid_from/valid_to`, surrogate version key, late correction; no overlap на business key |
| Где был адрес доставки заказа | Immutable shipping/order-address event | Snapshot заказа; не SCD «текущий адрес buyer» поверх прошлых заказов |
| Как менялся статус и обещание | Order status/promise events с event ID и временем | Event fact; current status как projection. Snapshot не восстанавливает прежние статусы/обещания |
| Как изменялся отзыв | Review version/change events с payload и источником связи | Сохранять версии/associations, не выбирать последнее без порядка/политики конфликтов |
| Что происходило при загрузке | Ingestion manifest/run/event metadata | Техническая lineage отдельно от business valid time; `_loaded_at` не source cursor |

Из текущего снимка можно начать историю **наблюдаемых** изменений после первого приёма. Нельзя придумать историю до него или объявить дату первой загрузки датой создания бизнес-сущности. Для SCD2 нужны правила одинаковых timestamps, опоздавших изменений и исправления прошлого; system time и business time не смешиваются. При отсутствии надёжного effective time храним observed_at с честной границей.

## 4. Новые сущности и чего пока нельзя считать

| Сущность / новая система | Ключ и уровень будущего факта | Что станет возможно после приёма |
|---|---|---|
| Корзина и её события | cart_id, event_id, product/quantity, event time, identity mapping | Воронка basket→order с согласованной атрибуцией; не из одних заказов |
| Частичная отгрузка / перевозчик | shipment_id, order-item allocation, carrier events | Отдельные deadlines и фактические этапы каждой shipment |
| Выкуп/возврат/возмещение | item/order return_id, refund_id, amounts/currency/time/reason | Net sales и доля возврата, различие delivered/выкуп; исправления как события |
| Комиссия и расчёт с продавцом | settlement_id, seller, fee/refund/tax event | Денежный поток/маржа при наличии себестоимости и договоров |
| Остатки и цена | warehouse×product×time snapshot + movements | Остатки аддитивны по складам, но не по времени; price history отдельно |

Новые many-to-many allocation требуют сумм весов/количеств и проверок. Order payment не превращается в payment каждого seller без распределения. `payment_installments=8` не создаёт восемь датированных денежных событий.

## 5. Full rebuild и безопасный incremental

Нужен source cursor/CDC или versioned snapshot с manifest, stable keys и delete semantics. Восемь CSV и `_loaded_at` такого договора не дают. Full rebuild остаётся эталонным путём.

Инкрементальная порция: immutable batch ID + checkpoint → типизация/валидация → dedupe по event/version key → применение insert/update/delete → пересчёт затронутых orders/marts → проверки → атомарная публикация checkpoint и данных. Повтор batch не меняет результат; поздний payment/review пересчитывает прежний order/month. Tombstone удаляет или помечает сущность по явной политике, не по исчезновению строки из неполного файла. Изменение ключа — отдельное событие/миграция, не случайный UPDATE связи.

Обязательные сценарии паритета full/incremental: дубли batch/event, out-of-order, late children, update в прошлом, delete/tombstone, повтор после сбоя до/после commit, schema drift и конфликт review payload. Сравнение — не только общий total: key/value multiset, связи, NULL, coverage, все Q1–Q10 и метрики по срезам. Время запуска исключается из логического сравнения. Все такие тесты сейчас pending.

## 6. Кандидаты после PostgreSQL

| Вариант | Когда включать в одинаковый benchmark | Цена/риск, который надо измерить |
|---|---|---|
| PostgreSQL + отдельные аналитические aggregates/replica | Отделение отчётной нагрузки и повторяющиеся запросы | Lag, refresh/restore time, дополнительное хранение и работа DBA |
| DuckDB | Локальный/пакетный аналитический сценарий по экспортам, сравнение одного analytical workload | Модель конкурентного доступа, доставка актуальных файлов, operational fit; не объявлять заменой многопользовательского сервиса |
| ClickHouse | Широкие scans/aggregates и конкурентная аналитика, когда baseline выявил потребность | Договор updates/deletes/dedup/CDC, типы NULL/numeric и freshness; те же correctness gates |
| Managed warehouse или lakehouse | Совместная работа, долгий retention и несколько движков/источников | Storage+compute+egress+catalog+ops; partition/small files/schema evolution, recovery и права |

Это кандидаты, без выбранной миграции или заявления превосходства. Способ переноса PostgreSQL→ClickHouse нужно выбирать по реальному источнику изменений; официально описаны [batch/CDC варианты](https://clickhouse.com/docs/integrations/clickpipes/postgres/inserting-data), прочитано 2026-10-28. Наличие коннектора не доказывает паритет нашей модели.

## 7. TCO, паритет, публикация и откат

За один горизонт, например месяц, считать:

`TCO = compute_hours×rate + storage_GiB×rate + backup + IO/requests + egress + licenses + ops_hours×labor_rate + migration/test_hours×labor_rate`.

Все rates — из датированной сметы, пока unknown; нулевые значения не подставляются. Добавить стоимость параллельного прогона и простоя. Сравнивать одинаковые workload, freshness, concurrency, retention, RPO/RTO и correctness, а не только дешевизну одного SELECT.

Переход: зафиксировать версию SQL/input и контракты → backfill в отдельную target-зону → shadow reads из обоих движков → проверить key/value/NULL/money/calendar/coverage и все ответы → нагрузочный и restore test → ограниченное read-only переключение потребителей с versioned endpoint → наблюдение → отдельное принятие владельцем. Dual writes без протокола не предлагаются.

Откат: оставить PostgreSQL/read endpoint и входные manifests доступными; хранить checkpoints и replayable batches, не удалять старую модель до завершения согласованного окна. Триггер отката — mismatch ответов, недопустимый lag/error или нарушение recovery/SLA; вернуть потребителей на предыдущую проверенную версию, остановить продвижение target checkpoint и сверить пропущенные batches. «Отменить deploy» без восстановления данных недостаточно. Проверить rollback заранее на изолированном стенде.

Источники и исходные альтернативы: [S17](../../research/internet-2026-10-28/synthesis/selected-findings.md), [backlog P2](../../research/internet-2026-10-28/backlog.md), [общий бриф](../implementation-brief-20261028.md). Стратегия полная по предмету, но её SLA, бюджет и технологический выбор остаются предложениями; результатов нагрузочного теста нет.
