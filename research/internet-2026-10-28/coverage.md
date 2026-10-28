# Покрытие исследования и его пределы

Input: `kiruha355/rwb_hak` / `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`; дата 2026-10-28 UTC. Программа после ориентирования — [v1](orchestrator/research-program-v1.md). Это отчёт о широте и пробелах, не обещание охвата интернета или approval архитектуры.

## Что сохранено

В [каталоге](catalog/all-findings.jsonl) **102 исходные записи**: 24 Gemini orientation и 78 Terra high corpus. Отклонённое не удалено. [Журнал](catalog/search-operations.jsonl) объединяет **138 записей операций** (38 orientation +100 corpus); смешанные search/open/API/локальные проверки не выдаются за 138 уникальных поисковых запросов. Счётчики — [JSON](catalog/coverage-counts.json), воспроизведение — [assemble_catalog.py](orchestrator/assemble_catalog.py). Статусы/primary/confidence агентов сохраняются как metadata, не наследуются как независимое подтверждение.

78 записей Terra ссылаются на **74 различных HTTP(S) URL**, 13 hostnames; несколько URL могут быть разделами одного источника или разными файлами одного проекта. Общий пул содержит 90 разных HTTP(S) URL плюс локальные/другие locators. Ни число URL, ни число доменов не измеряет правильность. Все key claims требуют review; корректность runtime чужих проектов не установлена.

## Темы → вопросы → источники → пробелы

| Seed / пакет | Решение и реально исследованные вопросы | Семейства источников / конкретный пример | Граница и следующий check |
|---|---|---|---|
| 1. Первичные Olist / B01 | 8 vs9CSV, версия, buyer/review keys, лицензия и источник копий | Olist Git/tree/commit, Kaggle ecommerce/marketing API; pinned `d9e4980…`; [B01](corpus/01_olist_identity/report.md) | Git bytes не отождествлены с Kaggle version; MIT Software не доказательство data dual licence; full primary column dictionary неполон. |
| 2. Реализации / B07 | detail→intermediate→mart, builds/tests, хорошие и плохие patterns | Pinned code Tu Nguyen, Disha Dhara, yzinchenko, tolamoye; ещё два seed только README; [B07](corpus/07_real_implementations/report.md) | Не исполнялись; два README не подтверждают реализацию. License неизвестна для части репозиториев: no code copy. |
| 3. Моделирование / B03 | normalized detail core vs constellation, grain, conformed/role date dimensions, natural/surrogate, bridges/allocation | Kimball primary methodology, Microsoft Power BI guidance, PG16 constraints; [B03](corpus/03_model_choices/report.md) | Архитектура не выбрана названием; обе альтернативы должны пройти одинаковые reconstruction/cardinality tests. |
| 4. Качество / B01/B02/B04 | missing children vs zero; unknown vs untranslated; review payload; деньги, типы, anomalies | CSV hash+stdlib/Decimal checks, source DDL/profile, official PG16 docs; [ранние проверки](orchestrator/validated-early-findings.md) | CSV≠DB/raw proof; исходный SQL366 и причины денежных расхождений unknown; transform policy не согласована. |
| 5. Метрики / B02/B05 | populations Q1/Q2/Q3; money components, repeat/cohort/RFM, late/lead/review weights | Tasks pinned candidate source; Kimball nonadditivity; NIST censoring; [B05](corpus/05_metrics_time_dashboard/report.md) | As-of/timezone/полнота неизвестны; 90дней/Aug31 не универсальный контракт. Нет cart/buyout/return/settlement событий. |
| 6. Dashboard / B05/B07 | decision-focused concept и контрпримеры fanout/overlapping distinct/ratings | Pinned Streamlit hudasf и miguelvotre, dbt semantic docs; SQL marts; [B05](corpus/05_metrics_time_dashboard/report.md) | Не проверены UI/runtime/full upstream semantics; условные code counterexamples, не обвинение всех данных. Рабочий UI не обязателен по handout, ambitious concept допускается. |
| 7. PG16 reproduction / B04 | fail-fast/transaction/rebuild, TRUNCATE MVCC, NULL/constraints, assertions, source manifest | Official PG16 psql/DDL/locks/isolation/numeric/time docs; [B04](corpus/04_pg_build_checks/report.md) | Fixture/DB/rollback/concurrency не запускались. Предложенные locks требуют проверки и согласования; одного REPEATABLE READ недостаточно против произвольного reload. |
| 8. Развитие / B06 | measurement→indexes/MV/partition→increments/SCD/CDC→engine comparison | Official PG16/dbt/DuckDB/ClickHouse/BigQuery/Iceberg; [B06](corpus/06_growth_evolution/report.md) | Нет SLA/workload/TCO benchmark; row-count threshold не установлен. Будущая сложность не отвергнута из-за знаний людей. |

## Языки и типы обращений

Журналы действительно содержат EN, PT-BR и RU запросы/чтение. По исходным labels всего 119 EN records, 4 PT-BR, 3 смешанных, 1 RU, 11 `sql/und/none`. Это **labels записей операций**, включающих fetch, а не надёжное число language-specific searches: регистр и составные labels разнородны. Большинство корпуса EN; PT-BR и RU — небольшой разведочный слой. PT-BR Olist README прочитан; русские handout/tasks/PDF исследованы подробно, но это не широкий RU internet search.

Примеры реально записанных намерений: Olist version/geolocation/marketing, SQL/dbt warehouse examples, PostgreSQL fail-fast/constraints/partition limitations, ecommerce cohort observation window. Точные строки и открытые URL — в package search-log и сводном JSONL. Предлагаемые слова поиска из Gemini report не считаются выполненными запросами. Время ряда вызовов сохранено только как session interval, не подменено выдуманной точностью.

Первичные материалы: dataset repo/API; case PDF и candidate upstream; официальная техническая документация; методология авторов Kimball/NIST; pinned open-source code. Вторичные материалы: mutable dictionary и учебные проекты. Самостоятельные peer-reviewed research papers отдельным слоем не собраны; методологические вопросы решались первичными руководствами, а не заявлением научного обзора. Power BI/Tableau/Metabase/Superset реализации не прошли глубокую проверку; реальные code examples здесь главным образом SQL/dbt/Streamlit. Эти пробелы сохранены, а не заполнены случайными ссылками.

## Очередь углублений

1. **P0, организаторская интерпретация:** официальный authority/ref/update channel, Q1/Q2 counts и Q3 amount/denominator, регламент150/155. Candidate URL найден и побайтно сопоставлен, полномочия и актуальные иные каналы unknown.
2. **P0, реализация будущей модели:** выбранные A/B и review representation; row/field accounting, null-aware round-trip, negative fixtures, transactional rollback и raw snapshot coordination. Это следующая инженерная задача после research и решения человека, не недостающая ссылка.
3. **P1, источник:** содержательный diff предыдущих review CSV, точная Kaggle↔Git версия/bytes, scope лицензии данных и полный primary dictionary. Не влияют на наблюдаемую FD этого pinned файла, но важны для будущих источников/атрибуции.
4. **P1, время/метрики:** extraction as-of, покрытие delivery/returns/settlement, смысл promised date/timezone. Без событий/метаданных дальнейший веб-поиск не восстановит отсутствующие факты; запросить владельца источника.
5. **P1/P2, измерение роста:** согласовать workload/SLA, затем выполнять benchmark/fixture в отдельно разрешённой среде. В этой работе не исполнялось.

Широкий corpus завершён как сбор; независимый отбор и итоговый synthesis имеют собственный статус в [индексе](../README.md). При новых интентах добавлять вопрос и evidence, не переписывая прошлый provenance или rejected alternatives.
