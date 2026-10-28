# Internet research RWB: итоговый синтез

**Сбор и независимый отбор завершены локально 2026-10-28.** Итог — исследовательские рекомендации, не решение команды и не работающая модель. Owner synthesis: Sol xhigh. Основные входы: `kiruha355/rwb_hak`, `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`; дополнительно прочитан `docs/idea-synthesis.md` на `fc84ecf98be8405058bc60453cc61af321b1b666`. Code/data baseline этим новым commit не изменён; merge не выполнялся.

## Короткий вывод

Наибольшую практическую пользу дают явные уровни данных, сохранение независимых фактов и связей, паспорта метрик, точная сверка денег и воспроизводимые проверки. Название архитектуры само по себе не защищает от ошибок. Normalized detail core и constellation остаются полноценными альтернативами; order-level витрины полезны поверх любой из них. Сложность выбирается по задаче и проверяемости, а не по текущим знаниям трёх участников: код пишут агенты, понимание развивается через explainer.

Полный амбициозный scope сохранён: модель, все 10 ответов и вброс, SQL build/checks, записка, концепция и обоснованные варианты реализации dashboard/semantic/lineage/AI-доступа, стратегия и доказательства работы ИИ. Checkpoint около 10:01UTC — промежуточный результат, не финальный deadline. Это исследование не меняло модель или runtime.

**Два особенно важных факта для защиты:**

- На 98665 заказах с items и payments exact `delta!=0` даёт 639/−1819.51; `abs(delta)>0.01` даёт 366/−1818.84. Число и сумма должны относиться к одному объявленному набору. Исходный SQL профиля и причины расхождений неизвестны.
- Все 99224 review-order пары уникальны, payload пяти полей функционально зависит от review_id на этом снимке. Pair fact и entity+bridge оба могут сохранить данные; dedup до одного review_id без сохранения связей их теряет. Вес по парам, ID и orders — разные метрики.

Метод и hashes: [ранние наблюдения](orchestrator/validated-early-findings.md), [независимый R1 CSV check](reviews/01_correctness/evidence/csv-check.json), [собственный Sol check](orchestrator/evidence/sol-independent-check.json). Это CSV evidence, **не DB/raw equality и не PASS core/mart**.

## Как сформирован и проверен корпус

После личного чтения PDF, handout/tasks/README, профиля и загрузчиков три Gemini3.8Flash medium сформировали ориентирование. Их 24 записи содержали полезные вопросы и неподтверждённые ответы; [quality gate](orchestrator/orientation-quality-gate.md) сохранил возражения. Пользователь явно выбрал Terra high для широкого поиска: семь пакетов дали 78 кандидатов. Три Terra xhigh затем независимо открывали ключевые источники и отобрали материал по correctness/data, model/reproducibility и jury/metrics/dashboard/roadmap. Sol разрешил разногласия и выполнил собственные CSV/источниковые проверки.

- [Широкий каталог](catalog/all-findings.jsonl):102 исходных записи, включая rejected/unresolved, не 102 подтверждённых факта.
- [Журнал](catalog/search-operations.jsonl):138 записей операций (100corpus+38orientation), не число уникальных searches.
- Terra corpus:74 различных HTTP(S) finding URLs/13hostnames; общий пул 90HTTP(S)URL. Повторные разделы одного сайта не считаются независимыми доказательствами.
- [Review matrix](catalog/review-matrix.jsonl):162 диспозиции по всем 102IDs. Это не majority vote и не человеческое принятие.
- [Покрытие](coverage.md):все 8 исходныхтем,7 пакетов, EN/PT-BR/RU, типы сайтов/кода, альтернативы и пробелы. EN преобладает; отдельный полный научный обзор, глубокий PowerBI/Tableau/Metabase/Superset и равный языковой охват не заявляются.

## Отбор:18 сильнейших результатов и кандидатов

[Полный shortlist с source→finding→задача→acceptance check](synthesis/selected-findings.md), [машинная версия](synthesis/selected-findings.jsonl). Основные группы:

| Группа | Что переносится в полный план | Статус |
|---|---|---|
| S01–S07: источник, grains, деньги, buyer/review/category | Manifest и raw provenance; детальные сущности; безопасные агрегации; exact comparator; адрес заказа; все review связи; unknown отдельно от missing translation | Узкие CSV observations проверены; архитектура/review representation остаются выбором. |
| S08–S12: типы/build/checks/контракты | NULL/zero/scale/timezone; fail-fast transaction и границы объектов; raw consistency; смысл checks; populations Q1/Q2/Q3 | Документированное поведение и proposed implementation; fixture/DB не выполнялись. |
| S13–S16: время, неаддитивность, dashboard, чужие проекты | Разные временные оси; unknown незрелых когорт; правильные веса; decision-focused интерфейс; pinned code patterns и исправленные контрпримеры | Semantic/UI choices — proposals. Чужие программы не запускались. |
| S17–S18: развитие и защита ИИ | Условная roadmap по workload/SLA/TCO; SCD/CDC при источниках; полная трасса requirement→decision→source→SQL→check→результат | Нет универсального предела строк PG, performance PASS или принятой технологии миграции. |

**Ключевые практические альтернативы:** A detail core + views versus B constellation; review pair versus entity+bridge; Q1/Q2 all versus delivered counts; Q3 item+freight versus payments и соответствующие denominators; day-level late versus timestamp comparison; commercial/logistics/quality dashboard и semantic/AI интерфейсы. Контрольная цифра, красота демо и популярность repo эти решения не принимают.

## Разногласия разрешены, контраргументы сохранены

[Решения Sol](synthesis/disagreements.md) отделяют observation от переноса pattern. Например, reject прямого join и adopt проверки против него совместимы; отсутствие собственного CSV check у одного reviewer не опровергает независимый замер другого.

Исправлены важные ошибки исходного поиска: причины 366/rounding/Boleto не доказаны; повтор review_id не доказывает NPS/split-cart; Gemini ошибочно обобщил потерю payload агрегата Tu Nguyen на весь проект — staging выбирает тексты/даты; pinned LICENSE этого repo MIT, не Apache2. Исправлен locator tolamoye: query payment-by-category L414–423. Утверждения `<5ms`, in-memory,5/50 млн строк, обязательных BRIN/monthly partitions и общего 90d/Aug31cutoff отклонены как установленные.

R2 также уточнил: требование инвентаризации/семантической сохранности не означает обязательного лексического дубля всех raw строк в core. `REPEATABLE READ` не решает TRUNCATE гонку автоматически; `ACCESS SHARE` и `SHARE` имеют разные права/влияние. Locks/CASCADE не являются скрытым разрешением менять raw/задерживать других.

## Новый main и общий банк идей

Прочитаны опубликованные [idea09](https://github.com/kiruha355/rwb_hak/blob/266bdfabc8707393a7e88c35411d22fa5a4983d3/idea/09-mput-ideas.md) и [idea10](https://github.com/kiruha355/rwb_hak/blob/266bdfabc8707393a7e88c35411d22fa5a4983d3/idea/10-mput-research.md). Это общий материал для обсуждения; наш индекс/правила не объявлены общекомандным consensus.

[Сопоставление fc84](synthesis/compare-main-fc84.md) поддерживает source-keyed control regression и уточняет спорные выводы: order-level carrier timestamp не доказывает виновного seller/carrier; latest review не доказанное «актуальное мнение»; ingestion time не надёжный source-change cursor. Дополнительно Sol подтвердил Q3:1.142198221source rows/units versus1.038537283distinct(product,seller)groups per delivered order. Второе — отдельная derived метрика, не автоматическое ожидание задания. Root документы не переписывались.

## Backlog и нерешённое

[P0/P1/P2 полный backlog](backlog.md) содержит конкретные результаты и acceptance checks, список того, что не переносить, и вопросы источнику. Приоритеты задают зависимости, а не сокращение до MVP. Regression controls привязываются к input manifest; build invariants не зашиваются только под пять вопросов.

Candidate organizer repository найден адресно: default main/ref `3da32d149bfa14dca3fdb0c5863d0771c38efbfc`, README/handout/tasks byte-equal нашим копиям. По этому ref доступны Q1–Q5 и обещание 5 ещё/вброса. Полномочия владельца и другие каналы не доказаны. [Evidence](orchestrator/evidence/organizer-candidate.json), [адресный разбор](orchestrator/requirements-targeted-check.md).

Остаются открытыми: рубрика 155 в PDF/150 в очищенной стенограмме; официальный канал/ref обновления; Q1/Q2 population, Q2–Q5 periods и Q3 components/denominator; source-as-of/timezone/promised-date; исходный payment SQL/причины, CSV licence scope и Kaggle↔Git version; фактическая загрузка raw и все model/runtime проверки. Уже известные пользовательские checkpoint/кто пишет код повторно не спрашиваем.

## Границы и передача

Выполнены: web search/fetch/API, статическое чтение pinned code/docs, собственные stdlib CSV/Decimal checks, проверка структуры каталогов и source links. Не выполнялись: DB/Docker/services, SQL build/core/mart, чужой internet code, benchmark/fixture/UI, установки зависимостей. Исходники и чужие writable-зоны не менялись; собственных commit/push/merge не было. Локальные технические audit/IDs исключены из публикации, evidence переносимо и не требует определённого харнесса.

Семь candidate packages и ранний evidence опубликованы коллегой на `266bdfabc8707393a7e88c35411d22fa5a4983d3` ветки idea-bank. Финальные synthesis/reviews/catalog этой порции — **ready_for_publication**, до возвращённого publication SHA не считаются опубликованными. [Manifest](publication-manifest.json) задаёт точные paths/hashes и исключения. Новые интенты принимаются через [intake](intake.jsonl), без потери прежних вариантов и provenance.
