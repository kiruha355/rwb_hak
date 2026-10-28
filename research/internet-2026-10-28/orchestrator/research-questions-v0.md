# Исходные проверяемые вопросы (кандидаты для ориентирования)

Не предписанная таксономия. Gemini должны оспорить, дополнить, сгруппировать и приоритизировать её по реальному кейсу.

| ID | Вопрос | Решение, которое изменится | Как проверить применимость |
|---|---|---|---|
| RQ01 | Какова точная версия и граница восьми CSV, их словарь и лицензия? | provenance, attribution, допустимые источники | pinned Olist ref, список файлов, сравнение с загрузчиком |
| RQ02 | Какая детальная структура выдержит неизвестные 5 вопросов без потери фактов? | normalized core/star/constellation и mart | ability to query each source grain; keys/cardinalities/reconciliation |
| RQ03 | Какие соединения размножают деньги/оценки, какие теряют заказы? | separate facts, preaggregation, bridge/allocation policy | constructed fanout counterexample; compare project cardinalities |
| RQ04 | Как представлять buyer identity, адрес заказа, reviews и категории? | natural/surrogate keys, unknown members, no silent dedup | keys from profiling; complete row accounting |
| RQ05 | Где проходит граница hard constraints и сохраняемых аномалий? | typed core, quality ledger/quarantine, fail-fast | bad syntax vs valid business anomaly; rows conserved |
| RQ06 | Как доказать сборку с нуля, повторяемость, raw immutability и отсутствие потерь? | transaction/build strategy, assertions, provenance | official PG16 behavior + proposed failure/rerun checks |
| RQ07 | Как задать метрики так, чтобы AOV/revenue/payments/repeat не противоречили друг другу? | metric contracts and marts | grain, status, time, denominator, non-additivity + controls |
| RQ08 | Какие новые вопросы о delivery/reviews/cohort корректно ответимы в этих данных? | extensibility and decision-focused dashboard | explicit censoring/observation window, missing timestamps, no invented facts |
| RQ09 | Что полезно перенять из существующих реализаций, что ошибочно? | implementation patterns and tests | actual code/commit/license; counterexample on our cardinalities |
| RQ10 | Что показать жюри и как документировать проверку ИИ? | concise defense and evidence chain | requirement→decision→source→check; no unverifiable claims |
| RQ11 | Какие реальные условия потребуют SCD, increments, CDC или другого движка? | staged roadmap | data availability and measured workload triggers, no magic row limit |
| RQ12 | Какие трактовки нужно уточнить у организаторов до реализации? | metric/constraint choices | distinguish contradiction from optional alternative; primary requirements |

Наблюдения Sol после чтения исходников: загрузчик скачивает mutable master, не проверяет checksum; core отсутствует; raw DDL/loader при запуске пересоздают/перезаливают raw, поэтому не могут служить командой сборки модели при требовании raw неизменяем. Это чтение кода, не runtime-проверка.

## Уточнения intake после запуска ориентирования

| ID | Проверяемый вопрос | Критерий различения |
|---|---|---|
| RQ13 | Что delivered позволяет утверждать о выкупе/возвратах? | Словарь источника + наличие/отсутствие событий; явно отделить proxy от наблюдаемого события |
| RQ14 | Review-pair fact или review entity + bridge: что сохраняет payload? | Проверка функциональной зависимости review_id→payload; сравнение конфликтующих полей, no silent dedup |
| RQ15 | Что доказывают разные адреса одного customer_unique_id? | Наблюдение об адресах отделено от гипотезы переезда; адрес заказа сохранён без выдуманной истории |
| RQ16 | Как точно определены 366 payment discrepancies? | Comparator, population, missing-child handling, NULL/zero, precision и знак явно заданы; прежнее число не подменяет метод |
| RQ17 | Какая версия CSV и какое окно наблюдения делают результаты воспроизводимыми? | Pinned ref/hash/header/count + explicit as-of/censoring rules; не считать хвост 2018 полным периодом |
