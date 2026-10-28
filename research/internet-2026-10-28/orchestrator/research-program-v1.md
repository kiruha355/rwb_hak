# Программа широкого ресерча v1

Owner: Sol xhigh; repository kiruha355/rwb_hak, main; inputs 2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e (2026-10-28). UTC: 2026-10-28 08:07.
Статус: in_progress. Это исследовательская программа нашей группы, не принятое командой архитектурное решение.

## От цели к проверяемым вопросам

Цель — модель, на которую могут опереться аналитики, а не воспроизведение пяти чисел. Проверяем решения по сохранности информации, корректности измерений, воспроизводимости, объяснимости и цене реализации в хакатоне. Пользователь подтвердил Terra high для широкого поиска после оценки качества Gemini; финальные 3 независимых проверки остаются Terra xhigh.

Ориентирование завершено: 3 Gemini medium, 24 candidate records. Полезные вопросы перенесены ниже, неподтверждённые ответы сохранены как исходный пул. [Quality gate](orientation-quality-gate.md) объясняет возражения. Результаты профиля коллег — входные claims, независимая проверка ещё нужна.

## Пакеты поиска и критерии завершения

| Пакет | Проверяемые вопросы / решения | Что различает альтернативы | Coverage исходных seeds |
|---|---|---|---|
| B01 Olist: provenance, identity, reviews | RQ01/04/14/15/17: версия 8 CSV, словарь, buyer/address, review pair/bridge, лицензия | pinned source/ref/hash; header/count; payload FD и конфликтующие поля; лицензия с scope, а не предположенное dual licensing | 1,4; часть 3 |
| B02 Money и populations | RQ03/05/07/16/19/20: item totals vs payments, exact comparator, Q1/Q2 count universe, Q3 denominator, installments | Decimal comparison; all/delivered/intersection/missing-only coverage; NULL vs zero separate; cause unknown без ledger; fanout counterexample | 4,5; часть 3 |
| B03 Детальная модель и развилки | RQ02/03/04/14/21: normalized core vs constellation, grains/keys, unknown members, allocation vs bridge | сохранность каждой source entity/field; no fanout guarantee от одного названия схемы; order mart не заменяет core; allocation явно derived | 3,4 |
| B04 PG16: build и доказательства | RQ05/06/10/17/21: fail-fast, transactions, constraints, deterministic rebuild, data lineage, self-checks | docs по реальному PG16; proposed raw→core accounting и failure/rerun checks; warnings vs blockers; no unchecked runtime PASS | 7; часть 4 |
| B05 Метрики, время, dashboard | RQ07/08/13/17/19/20: наблюдаемое vs proxy, cohort/as-of, SLA, review weighting, decision-focused dashboard | formula/grain/status/time/denominator/missing/nonadditivity; immature cells unknown; exact Olist dashboard/semantic examples; без обязательного 90d или общего Aug31 cutoff | 5,6 |
| B06 Рост и стоимость | RQ11/21: текущий Postgres, indexes/MV/partitioning, SCD/increments/CDC, DuckDB/ClickHouse/warehouse | триггеры нагрузки/SLA и этапность, primary docs и границы benchmark; no universal row threshold; history нельзя восстановить из snapshot | 8,7 |
| B07 Реальные реализации и контрпримеры | RQ09/02/03/06/10: конкретный SQL/dbt/PG проект и tests | immutable repo commits/paths/lines/license; отдельно detail layer и marts; проверить наличие файла и теста, не считать popularity correctness; не запускать код | 2,6; части 3,7 |

7 пакетов выбраны по решениям; покрытие не требуется делать равным. Геолокация, ML, realtime UI, корзины/returns/commissions не исследуются ради количества. Имеющие смысл будущие сущности отмечаются later и отделяются от данных сейчас.

## Дополнительные durable RQ

- RQ18 — первичный upstream организаторов, актуальный tasks ref, регламент/рубрика и переносимый workflow. Адресная проверка Sol в [requirements-targeted-check.md](requirements-targeted-check.md): upstream/онлайн 6–10/вброс/сроки пока unresolved; документирован import AGENTS, не запускался Claude.
- RQ19 — недоопределённые Q1/Q2 populations и Q3 item+freight vs payments/status/time/denominator. Контрольные числа не решают трактовку.
- RQ20 — что означает строка payment_sequential vs payment_installments; нет отдельной даты/события списания на каждый взнос. Можно ли вообще называть сумму cash_collected/cashflow без дополнительных данных?
- RQ21 — как сохранить границы наблюдаемого и изменяемого при новых источниках/late facts/schema change, не выдумывая историю, и какие проверки переживут вброс?

## Метод и стандарт evidence

1. Primary docs/dictionaries/source files, затем pinned code, затем статьи/notebooks как идеи. EN/PT-BR/RU по смыслу. Каждый пакет сохраняет реальные queries, открытые URL и negative results. Альтернативы/контрпримеры обязательны; квоты находок нет.
2. Findings по schema brief; дополнительно claim-specific evidence, точный source locator, собственная дедукция отдельным полем inference. Homepage URL не доказывает конкретный технический claim. Self-authored methodology note не первичный source.
3. Существование API/catalog/repo не означает inference correctness/runtime correctness/data semantics. Согласие агентов не заменяет evidence.
4. Собственный лёгкий streaming-read pinned CSV стандартной библиотекой допустим только B01/B02: без сохранения полных CSV, без DB/сервисов/зависимостей, без выполнения чужого кода. Сохранять свой небольшой reproducer и агрегатные результаты/хеши/coverage, ограниченные обезличенные examples. Не загружать полные datasets/transcripts в Git.
5. Копирование внешнего кода — только с подтверждённой лицензией и attribution; предпочтительнее source locator и собственный paraphrase. Незнакомая лицензия = no copy, но ссылку сохранить.
6. Работать только в назначенном подкаталоге corpus. Корневые инструкции и реестры других writers не менять. Публикация по согласованному ownership/Git protocol; несколько процессов не меняют один index одновременно. Локальные параметры харнесса не являются требованиями для коллег на других машинах.
7. Stop criterion пакета: есть evidence по ключевой развилке и конкурирующему варианту, ограничения/контрпример, concrete task→acceptance check; оставшиеся неизвестные явно перечислены. Не добавлять ссылки без влияния на решение.

## Следующая проверка

Уточнение пользователя 08:31Z: полный амбициозный scope, а не минимальный demo. Знания команды не ограничивают качество реализации; сложные решения объяснять в explainer. Gate проверяет доказательства и применимость, не ограничивает scope. Checkpoint около 10:01Z — промежуточная демонстрация конкретного результата, не финальный deadline. Вопросы о deadline/SQL-writer повторно не задавать. Исследовательский тред по-прежнему не меняет code/runtime.

После всех B-пакетов Sol объединяет исходный pool без удаления reject/unresolved, строит coverage/query/language/source-type matrix и очередь точечных пробелов. Затем 3 новых Terra xhigh: correctness/data; modeling/implementation/reproducibility; jury/metrics/dashboard/roadmap. Они открывают ключевые источники сами. Итог Sol разрешает разногласия, даёт shortlist, P0/P1/P2 и вопросы организаторам; архитектура остаётся proposal до решения человека.

