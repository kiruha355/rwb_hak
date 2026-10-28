# Quality gate после трёх Gemini orientation

Owner: Sol xhigh. UTC review: 2026-10-28 08:03:40.
Repository `kiruha355/rwb_hak`, main; input SHA `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`.
Статус: `ready_for_review` методики; широкая фаза ещё не начата.

Все три задания Antigravity `gemini-3.8-flash-medium` завершены. Их 24 записи остаются **candidate/unverified**, а не 24 подтверждёнными находками. Исходные отчёты не переписываются: ошибки сохраняются для проверки ИИ. Согласие агентов не считается независимым доказательством.

## Что полезно для программы

- Разделение требований, выбранных контрактов и наблюдений профиля.
- Проверка `review_id → (score,title,message,creation,answer)` перед выбором pair/bridge.
- Матрица payment comparator: population, component totals, missing children, NULL/zero, precision, sign.
- Разделение детального core и агрегатных marts; проверка адреса заказа и buyer identity.
- Явное окно наблюдения для delivery/cohort и workload triggers вместо моды на движки.

Это полезные вопросы/предложения. Они не доказывают ответы и не являются утверждённой архитектурой.

## Конкретные возражения Sol

| Исходный claim / locator | Что с ним не так | Статус и следующий check |
|---|---|---|
| `01_problem/FIND-01-PROB-008`, `03_value/FND-VAL-003`: 366 расхождений вызваны ваучерами, Boleto discounts, округлением рассрочек/фрахта/частичными отменами | В `docs/profiling.md:44` есть итог, но нет SQL происхождения и причин. Evidence агента — собственный рассказ и homepage URLs, не журнал операций. `payment_installments` не означает отдельную строку на каждый взнос. | **reject as established cause**. Сначала Decimal comparator/coverage на pinned CSV; причины могут остаться unknown. |
| `01_problem/FIND-01-PROB-006`, `02_choices/FND-006`, `03_value/FND-VAL-007`: единый survey/NPS на split orders объясняет review_id; payload одинаков | Не приведён конкретный первичный discussion URL или результат сравнения payload. Одно утверждение повторяется в трёх ответах. | **unresolved**. Прямой payload/FD test; семантика survey vs association; не называть NPS оценку 1–5. |
| `02_choices/report.md §3`: constellation — единственная правильная архитектура, fanout 0% | Наличие отдельных фактов не запрещает неверный fact-to-fact JOIN. Детальный 3NF core тоже сохраняет grain. Агрегированный mart не доказывает потери в core, если staging/detail сохранены. | **reject exclusivity/guarantee**. Сравнить реальные схемы и queries по одинаковым acceptance checks. |
| `03_value/FND-VAL-006` и scaling evidence: весь PG workload в shared_buffers, запросы <5ms, этапы <5M/5–50M/>50M, обязательные monthly partitions/BRIN | Runtime не запускался, аппаратные/нагрузочные требования неизвестны. Конкретные пороги не выведены из primary docs или измерений; выбор BRIN/partitioning зависит от физической корреляции/сканов/плана. | **reject performance claims and thresholds**. Официальные docs, план измерений и условная roadmap; benchmark не заявлять. |
| `01_problem/FIND-01-PROB-003`: 20 tail orders, затем '(1 in Sep, 4 in Oct)' и extraction stopped Aug31 | Внутренняя арифметическая несогласованность; причина/граница извлечения не доказана. Пустой ноябрь также не доказывает operational pause. | **reject causal story**. Проверить даты/распределения на pinned источнике; отделить purchase window и observation horizon. |
| Все отчёты: общее отсечение `<2018-09-01` для всех метрик и обязательные 90 дней retention | Окно Q1 явно задано только для Q1. Для других вопросов нужно обосновать cohort, доступность событий и знаменатель. Отсечение purchase не равно доступности последующей delivery. 90 дней — один возможный контракт. | **reject as universal rule**. Раздельные metric contracts и immature-cohort NULL, точный as-of неизвестен. |
| `01_problem/FIND-01-PROB-002`: GitHub MIT позволяет permissive data use / dual licensing | Наличие LICENSE для Software не устанавливает область лицензии CSV и не доказывает предоставление данных на выбор под двумя лицензиями. | **unresolved**. Проверить Kaggle metadata/attribution и scope repo license; не давать юридического вывода. |
| `02_choices/FND-003..005`: repo code / licenses / main refs | Не закреплены immutable commits. Локальные SQL-файлы не доказывают существование и точное содержимое upstream. Ошибка одного mart не доказывает потерю всех detail в проекте. | **unverified**. Открыть repo, ref/tree/file и LICENSE самостоятельно. До этого не копировать код и не публиковать его как достоверный source snapshot. |
| Addresses: 'not relocation' → адрес обязательно immutable и SCD2 всегда antipattern | Отсутствие доказательств переезда верно; причины office/gifts тоже лишь возможны. Snapshot заказа полезен, но будущие изменения/исправления адреса требуют явного контракта. | **adopt epistemic boundary; model is proposal**. Сохранять наблюдаемый адрес заказа; не выдумывать residential history. |

## Решение о следующем поиске

Gemini выдал пригодные формулировки вопросов, но систематически смешал evidence, гипотезы и требования. Предложение: широкий корпус собирать `codex / gpt-6.1-terra / reasoningEffort=high` (вариант, названный пользователем), финальные три независимые оси отбора оставить Terra **xhigh**. Переход фиксируется отдельным явным выбором; этот документ сам по себе провайдера/модель не меняет.

В широком brief нужны ограничения: exact URL, immutable commit, field-specific evidence, компактный evidence, own inference label, no homepage-only proof, no invented causal explanations, no universal row thresholds. Если источника нет — unresolved; заполнение квоты не требуется.

## Границы

Sol прочитал findings всех трёх и соответствующие evidence/разделы отчётов; полную валидность внешних ссылок и CSV не утверждает. Независимо открыт pinned README и LICENSE Olist: [README](https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/README.md), [LICENSE](https://raw.githubusercontent.com/olist/work-at-olist-data/d9e49802f3e92d09ee94ab9ccc5e457f207a8959/LICENSE). README — отдельное Olist hiring exercise; его семидневный срок **не является сроком RWB**. Данные/SQL/runtime здесь не запускались.
