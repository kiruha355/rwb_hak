# Независимая проверка модели aab62d7

**Результат: PASS в пределах малых синтетических проверок actual SQL. Подтверждённых новых дефектов модели не найдено.** Это не полный DB PASS на Olist, не приёмка приложения и не проверка нового механизма истории.

Вход: `aab62d7a59f196be051df12466fb21c0da4659b9`, ветка `t3/integrate-q6-q10-marts`. Требования организаторов: `558f0f6a38110acc9fcf4386a7e53ece973aedf5`, `docs/tasks.md`. Финальный запуск: **2026-10-28 14:11:20–14:11:32 UTC**. PostgreSQL **16.15**, установленный ранее; собственный Unix socket, TCP отключён, `shared_buffers=16MB`, `work_mem=1MB`, максимум 5 соединений, без parallel workers. Сервер остановлен; его временные данные и копии SQL удалены. Другие серверы и сессии не использовались.

## Метод и доказательства

- [run.py](run.py) извлекает файлы из точного Git input, а не из общего dirty checkout. Фактически выполняет `bash scripts/build-model.sh build`, `answers`, `check` и все стадии `model/build.sql`, включая проверки. Никакие source/model-файлы проекта не изменяются.
- [fixture.py](fixture.py) задаёт **24 заказа, 12 позиций, 11 платежей, 16 пар отзыв—заказ**, 5 товаров и 2 продавцов. Это специально сконструированные данные; Olist не загружается в PostgreSQL.
- [oracle.py](oracle.py) вычисляет ожидаемые значения по словарям fixture на Python/Decimal, без чтения production SQL и без контрольных цифр Olist. Проверяются ключи, отсутствие дубликатов и значения; допустимое расхождение дробных результатов `<1e-12`.
- Базовый запуск: **1 678 сравнений значений** по 17 группам результатов и дополнительному selector Q7. Отдельно проверены eligibility нового статуса, разные дедлайны и независимость интервалов доставки. Это количество сравнений, а не 1 678 независимых бизнес-сценариев.
- [summary.json](results-ready/summary.json): результаты baseline, пяти metamorphic-вариантов, 11 мутаций, шести отрицательных входов и lifecycle. [baseline_actual.json](results-ready/baseline_actual.json): реальные строки PostgreSQL. [source_manifest.json](results-ready/source_manifest.json): Git blob и SHA256 каждого извлечённого файла. [commands.json](results-ready/commands.json): команды, коды выхода, хеши SQL stdin и время.
- Все логи сохранены в [logs.tar.gz](results-ready/logs.tar.gz), хеши отдельных файлов — [log-manifest.json](results-ready/log-manifest.json). Основные build/error-логи также оставлены текстом в `results-ready/logs/`. Секретов, CSV и PGDATA в пакете нет.

## Различающие случаи

Номера source-строк ниже относятся к **aab62d7**, а не к текущему main. Это наблюдения об исполнении заявленного контракта, а не новые утверждения о выбранной бизнес-политике.

| Область и source | Контрпример для ошибочной реализации | Фактически получено |
|---|---|---|
| Fanout: `model/40_mart.sql:168–239` | У `fanout` 4 позиции × 2 платежа × 3 отзыва; прямой JOIN деталей размножил бы деньги | Одна строка заказа; `order_gmv=73`, `payment_amount=12`, counts 4/2/3. Q2 считает только позиции соответствующего продавца |
| Child 0/1/many, NULL/0: `model/40_mart.sql:182–228` | Нулевой заказ и отсутствие дочерних денег нельзя свести к одному значению | `zero`: GMV/payment **0/0**; `no-child`: **NULL/NULL**, counts 0/0; `missing-money`: **NULL/NULL**, counts 2/1. Присутствуют все четыре класса child coverage |
| Категории: `model/10_dims.sql:233–268`, `model/50_answers.sql:155–197` | NULL-категория, известная без перевода, буквальное имя `unknown`, неиспользуемый член | Разные ключи `unknown`, `pt:untranslated`, `pt:unknown`, `pt:unused`; строки сохранены. При неполных ценах total/share NULL; в варианте `complete_money` проверены числовые доли |
| Новый статус: `model/10_dims.sql:157–173`, `model/55_answers_block_b.sql:49–58` | `returned_custom` отсутствует в заранее известных восьми статусах | Заказ сохранён, `is_revenue=false`; Q8 содержит его с долей **1/24** и общим знаменателем 24 |
| Q6: `model/55_answers_block_b.sql:5–24` | Два лидера с тремя разными ценами; одна цена продана дважды в один день; у лидера есть NULL цена/дата | Оба лидера `a,b`; для `b`, 2018-01-01, price 20 — **2 единицы**. NULL-группы и unknown-price count сохранены; добавление non-revenue цен меняет только соответствующую популяцию |
| Q7: `model/55_answers_block_b.sql:27–46`, `answers/q06-q10/q07.sql:2` | Orders count, известная длительность и известное опоздание имеют разные покрытия | SP/all: orders **11**, duration denominator **7**, late denominator **8**; timestamp lateness **3/8=37.5%**, mean **10.25/7** суток. SP/delivered orders **10**, те же измеримые denominators |
| Порог Q7 | Различить 499/500/501 и all/delivered, не строя большой fixture | Масштаб **1/2/3 при пороге 2**: K1 исключён, K2/all включён, K2/delivered исключён, K3/delivered с двумя заказами включён. Подменяется только `500::bigint` в настоящем answer selector; оригинальный selector даёт пустой результат |
| Даты: `model/40_mart.sql:396–426` | Отрицательное purchase→delivery, NULL purchase, NULL estimate, отрицательное purchase→carrier | Отрицательная длительность NULL, но известное опоздание сохраняется. Для `carrier-negative`: purchase→delivery **1**, purchase→carrier **NULL**, carrier→delivery **2**. Нерелевантная аномалия не удаляет остальные интервалы |
| Payload отзывов: `model/20_facts.sql:175–199`, `model/40_mart.sql:348–372` | Один `review_id` у двух заказов с разными оценкой и текстом | Обе полные пары сохранены. У `shared-review` variants **2**, associations **2**, conflict **true**, общий representative payload **NULL** |
| Q10: `model/55_answers_block_b.sql:100–139` | Оценки `{5,5,1}`, `{5,6}`, `{6}`, `{NULL}`; NULL длительность и отдельный late denominator | В группе 5/within_score **3 заказа**, duration denominator **2**, late denominator **3**, среднее **2.125**, timestamp lateness **1/3**. Single-score-only: **1 заказ**, duration NULL, late **0/1**; повтор 5 не удваивает заказ |
| Q9: `model/55_answers_block_b.sql:62–95` | Покупки 2017-12-31 23:59:59, 2018-01-01, 2018-12-31 23:59:59, 2019-01-01 и NULL | В YY/2018 только **2 платежа**, сумма **10**, средние части **2**. До/после/NULL остаются в all_snapshot, но не в purchase_2018. Платежи не размножаются позициями/отзывами |

Порог 500 на буквальных 499/500/501 строках **не исполнялся**: проверена точная форма исходного selector и поведение того же selector на масштабе 1/2/3. Это сознательная граница small fixture.

## Metamorphic-проверки

Все пять вариантов проходят тот же независимый oracle; реальные строки сохранены в `results-ready/*_actual.json`.

1. `more_children`: дополнительный платёж и повторная оценка того же заказа. Q1/Q2/Q4/Q5/Q6/Q7/Q8/Q10 и review coverage совпадают с baseline; платёжные метрики меняются согласно новой строке.
2. `item_replication`: повтор позиции с новым item ordinal. Единицы и деньги растут ровно на одну позицию, число заказов и число различных цен сохраняются.
3. `nonrevenue_price_leader`: новые цены товара в `returned_custom`. Победитель all_statuses меняется, delivered — сохраняется; выручка delivered не получает эти позиции.
4. `permuted_input`: обратный порядок строк во всех восьми таблицах. Результаты сохраняются, без выбора «первой попавшейся» строки.
5. `complete_money`: неизвестные компоненты заменены известными значениями **только в новой fixture**. Проверены восстановившиеся суммы и числовые доли Q5; исходный `raw` проекта не редактировался.

## Чувствительность к мутациям

**11 из 11 убиты.** Мутации применялись исключительно к извлечённым временным копиям настоящих model/answer-файлов, затем выполнялся actual build wrapper. Это не подставные Python-результаты.

| Мутация | Обнаружение |
|---|---|
| LEFT JOIN платежей → INNER JOIN | Actual `core invariant checks failed` — потеря childless заказов |
| Неизвестная выручка → 0 | Actual `core invariant checks failed` |
| Q6 DISTINCT price → количество строк | Oracle: distinct_prices **4 вместо 3** |
| Q7 late denominator → все заказы | Oracle: **18.1818% вместо 25%** в calendar-day/SP/all |
| Q7 `>=` → `>` | Oracle: исчезли K2/all и K3/delivered на точной границе масштаба |
| Q8 child count=0 → count=1 | Oracle: **2 вместо 14** delivered заказов без позиций |
| Q9 верхняя граница `<2019` → `<=2019` | Oracle: **3 вместо 2** платежей YY |
| Q10 убрать DISTINCT (order,score) | Oracle: **4 вместо 3** заказов с оценкой 5 |
| Q10 denominator → все ассоциированные заказы | Oracle: **0 вместо NULL** при нулевом late coverage |
| Допустить отрицательную длительность | Oracle: **−2 вместо NULL** |
| Выбрать payload при конфликте review_id | Oracle: дубликаты result key `review_id` |

Точные before/after, хеши, детектор и первое расхождение находятся в `summary.json`. Мутации доказывают чувствительность к этим ошибкам; они не являются найденными дефектами немутированного snapshot. Закрытые R1/R2 и старое замечание DROP inventory не переоткрываются.

## Lifecycle и отрицательные входы

На baseline исполнены clean build, rebuild, actual answers/check entrypoints. Сравнивались строки всех raw/core/mart relations, определения views и constraints; из сравнения исключён только `core.check_results.checked_at`. Rebuild не меняет эти отпечатки. Raw до/после build/rebuild совпадает; его fixture-колонки отдельно равны ожидаемым входным строкам.

После всех стадий/checks временный `model/build.sql` получил исключение `ADVERSARIAL_LATE_FAILURE_AFTER_ALL_CHECKS`. Actual wrapper завершился с psql exit 3; полный отпечаток raw/core/mart до и после совпал. Этот эксперимент проверяет rollback на малой fixture.

Каждый из шести отрицательных входов также привёл к exit 3 и совпадению отпечатка ранее committed core/mart: duplicate item key (`23505`), orphan product (`23503`), цена NaN, пробельный order_id, невалидная дата, дата с дробными секундами. Для последних четырёх достигнута явная диагностика `Input type/key precheck failed`.

Первый прогон [results-run01](results-run01/summary.json) остановился именно на дробных секундах в year-boundary fixture. `model/05_typecheck.sql:82–103` и `model/CONTRACT.md:18–23` явно требуют формат без дробей; это **наблюдение ограничения контракта**, не новый баг. Границы базовой fixture приведены к секундам, случай дробей сохранён как отрицательный. Первый отказ, полный лог и тогдашний runner сохранены. Промежуточные успешные прогоны сохранены архивами с [проверенными хешами](archive-manifest.json).

## Локальные CSV

[csv-observations.json](csv-observations.json) получен [стриминговым скриптом](csv_probe.py). У всех **8 файлов / 550 759 строк** совпали SHA256, header и row count с `aab62d7:tests/model/input-manifest.lock.json`. CSV не копировались и не загружались в БД. Наблюдаются 349 повторных ассоциаций одной оценки заказа, 9 нулевых платежей, 2 нулевых installments, 8 delivered без фактической даты, 610 товаров без категории, 13 товаров в известных категориях без перевода. Конфликтующий payload в PG fixture — намеренный стрессовый вход; он не объявляется обнаруженным свойством текущего Olist.

Эта проверка связывает локальные файлы с опубликованным input lock. Она не устанавливает CSV→реальный raw→core/mart equality и не выдаёт новые итоговые Q6–Q10 из полного core.

## Что осталось

- Полный Olist lifecycle с CSV/raw equality, полные итоговые ответы, performance/plans и приложение не проверены.
- Новая реализация category history отсутствует в aab62d7; её runtime/rebuild/as-of/restatement и новый address regression требуют отдельной задачи на опубликованном SHA. Адресные исходники не изменялись и работа действующего Sol не дублировалась.
- Named variants проверены в их заявленном смысле. Выбор окончательной бизнес-политики, официального restatement и authority человека не подменяется этим PASS.
- Подтверждённых новых model findings с контрпримером нет; [findings.json](findings.json) содержит пустой список дефектов и явные ограничения. Произвольные входы вне проверенных сценариев и будущие изменения модели этим результатом не покрыты.

## Воспроизведение

Требуются существующие `python3`, PostgreSQL 16 по `/opt/homebrew/opt/postgresql@16/bin` и Git-объекты aab62d7/558f0f6. Установок и сторонних Python packages нет.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 verification/adversarial-20261028/run.py --output recheck-aab62d7
PYTHONDONTWRITEBYTECODE=1 python3 verification/adversarial-20261028/csv_probe.py --csv-dir /Users/a/rwb_hak/data --output verification/adversarial-20261028/csv-recheck.json
```

`run.py` разрешает новый output только внутри OWNED, создаёт только собственный server/runtime и удаляет их после остановки. Существующие endpoints не используются. Логи из архива читаются без извлечения, например:

```sh
tar -xOf verification/adversarial-20261028/results-ready/logs.tar.gz logs/mut_q9_includes_next_year_q9.log
```

Код fixture/oracle/runner и текст отчёта подготовлены ИИ; результат проверен фактическим PostgreSQL, независимым вычислением ожидаемых значений, отрицательными входами и мутациями.
