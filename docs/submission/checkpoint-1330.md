# Чекпоинт 13:30 МСК · 10:30 UTC

**Показываем за 5–7 минут:** готовый код сборки и модели, реальные строки одного заказа и проверяемые малые проверки. **7 справочников + 4 детальных факта**, Q1–Q5 реализованы с вариантами. PostgreSQL/core, повторная сборка и rollback ещё не выполнены; Q6–Q10 ждут условий. Это первый чекпоинт, не окончательная сдача.

[HTML-hub без сервера](index.html) · [HTML-показ](presentation.html) · [Заказ целиком](order-example.json) · [Все материалы](README.md)

## Кто и что открывает

«Ведущий», «модель», «проверки» — роли на показ, не назначение конкретных людей. Один человек может вести все три роли; второй участник должен уметь продолжить по открытому файлу.

| Время | Роль | Что открыть / сделать | Что объяснить |
|---|---|---|---|
| 0:00–0:40 | Ведущий | Этот файл или [hub](index.html), затем [восемь источников](source-guide.md) | Что есть в данных, что сдаём; корзин/выкупа/возвратов нет |
| 0:40–1:35 | Модель | [Связанный заказ](order-example.json) и mapping ниже | Один заказ, 1 item, 3 payments, 1 review pair; разные ключи и суммы |
| 1:35–2:35 | Модель | [CONTRACT](../../model/CONTRACT.md), [10_dims](../../model/10_dims.sql), [20_facts](../../model/20_facts.sql) | 7 dims + 4 facts; buyer/context, natural keys, все 47 бизнес-полей; raw неизменен |
| 2:35–3:35 | Модель | [40_mart](../../model/40_mart.sql): `WITH items`, `payments`, `reviews`; [50_answers](../../model/50_answers.sql): `q03_average_order` | Почему сначала независимые агрегаты; price vs GMV vs payment; разные знаменатели |
| 3:35–4:45 | Проверки | Команды A–C ниже; [verification](../../answers/verification.json), [90_checks](../../model/90_checks.sql) | Что уже проверено offline/static и что эти проверки не доказывают |
| 4:45–5:30 | Проверки | [build wrapper](../../scripts/build-model.sh), [runbook](../build-runbook.md), [RESULTS](../../answers/RESULTS.md) | Одна транзакция с checks, raw-пауза — обязанность оператора; DB-проверки ещё pending |
| 5:30–6:30 | Ведущий | [Матрица решений](#восемь-решений-для-показа) и [вопросы жюри](#короткие-ответы-жюри) | Причина→альтернатива→проверка. Новые вопросы поддерживает детализация |

**Версия на 10 минут:** ещё 1 мин на Q1/Q4 окна и count-варианты, 1 мин на [дашборд](dashboard-concept.md), 1 мин на [историю/нагрузку/откат](growth-strategy.md), 30–60 с на вопрос слушателя. Не тратить время на полный research-корпус и все 17 развилок; подробности остаются в [брифе](../implementation-brief-20261028.md).

## Точные безопасные команды показа

Запускать из корня `/Users/a/rwb_hak`. Не выполнять setup/reset/Docker/VM и не устанавливать пакеты. HTML открывается как локальный файл; сервер не нужен. Если малый check уже подтверждён и время ограничено, открыть сохранённое свидетельство и назвать метод, вместо повторения всего набора.

**A. Настоящий заказ из CSV, не ответ core:**

```sh
python3 docs/submission/order-example.py
```

Ожидается exit0, JSON `method="CSV read-only; not loaded raw/core; no SQL executed"`; counts `orders=1, items=1, payments=3, review_pairs=1, rows_in_naive_inner_join=3`; суммы price=29.99, freight=8.72, GMV=38.71, payments=38.71. W-12 выполнил эту команду с `--output docs/submission/order-example.json`; результат сохранён. Никаких запросов к БД скрипт не делает.

**B. Малые синтетические проверки настоящего SQL mart/answers:**

```sh
python3 answers/check_offline.py
```

Ожидается exit0 и компактная строка JSON: `status="offline_only"`, `engine="DuckDB 1.5.2"`, `checks_passed=93`, `postgresql_executed=false`. Используется уже установленный DuckDB, один поток, лимит памяти 128MB, in-memory. Не добавлять `--report`: сохранённые чужие артефакты на показе не перезаписываются. При недоступном импорте открыть [готовый отчёт](../../answers/verification.json), назвать ограничение и продолжить; установку на Mac не начинать.

**C. План PostgreSQL-негативных проверок, без их исполнения:**

```sh
python3 scripts/verify-model.py --plan
```

Ожидается exit0, `status="pending_db_execution"`, 16 cases, `missing_stages=[]`. Это проверенный план изолированных fixtures, **не 16 прошедших DB-кейсов**. Показать `fractional_scale_preserved`, `review_payload_conflict_retained_warning`, `calendar_gap_detected` и `compensating_order_errors_detected`.

**Запасные команды, если жюри просит воспроизводимость:**

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/model -p 'test_*.py' -v
python3 answers/static-check.py
bash -n scripts/build-model.sh
make -n build check control answers manifest rebuild-check
python3 docs/submission/verify_pack.py
```

Ожидаемые результаты: 14 unittest `OK`; static-check — `OK (19 files); no DB executed`; shell syntax — exit0 без текста; `make -n` печатает команды, не выполняет их; W-12 validator — `method=static_only`, PostgreSQL=false. Команды не связаны через `;`: код выхода каждой виден отдельно. На чужой машине число static files/версия может отличаться; сверить хеши перед сравнением.

По **прямому сообщению координатора** перед этим чекпоинтом он независимо повторил 14 unittest, 93 DuckDB checks, static19, wrapper dry-run и plan16, все exit0. W-12 не присваивает себе эти прогоны. Сохранённый owner-отчёт W-10 — [verification.json](../../answers/verification.json); wrapper dry-run и границы — [runbook W-09](../build-runbook.md#выполненные-малые-проверки-w-09). Для независимого повторения координатора отдельный run-log/ref в поручении не указан: это явно отмеченное сообщение, а не выдуманный файл evidence.

## Один реальный заказ: источник → SQL

`order_id = e481f51cbdc54678b7cc49136f2d6af7`, статус delivered, покупка `2017-10-02 10:56:33`. Источник — связанный срез восьми локальных CSV, выполненный W-12; [воспроизводимый скрипт](order-example.py), [результат](order-example.json). Это небольшой учебный пример для объяснения mapping, не полный экспорт датасета и не результат core.

| Наблюдение CSV | Куда идёт по нашему SQL | Что показать человеку |
|---|---|---|
| `customer_id=9ef432eb…`, buyer `7c396fd4…` | `dim_customer_context` + `dim_customer`; оба ключа на `fact_order` | Контекст и устойчивый buyer различаются |
| Customer ZIP `3149`, `sao paulo/SP` | Исходный текст сохраняется; derived ZIP `03149` | Нормализация не переписывает наблюдение |
| Item `1`, product `87285b34…`, seller `3504c0cb…` | PK `(order_id,order_item_id)` в `fact_order_item` | Одна единица; price29.99, freight8.72 |
| Payments seq1/2/3: 18.12,18.59,2.00 | Три строки `fact_payment`, PK order+sequence | Независимая сумма 38.71 |
| Review `a54f0611…`, score4 | `fact_review`, PK review+order; payload сохраняется SQL | Связь не дедуплицируется по одному review_id |
| `utilidades_domesticas→housewares` | `dim_product→dim_category` | Перевод необязателен, категория остаётся известной |
| Seller `maua/SP`, ZIP9350 | `dim_seller`, raw ZIP и derived09350 | Продавец связывается через item, не весь order amount |

Наивный JOIN даёт три строки: item price становится 89.97 вместо 29.99, item+freight — 116.13 вместо 38.71. В этом примере payment sum не размножается, потому что item и review по одному. Нельзя переносить эту случайную сохранность payment sum на другие orders. Общий контрпример 2×2×3 разобран отдельно.

Подготовленный [order-example.sql](order-example.sql) использует **core** и независимые CTE. До PostgreSQL-run его только открываем и объясняем. После проверенной сборки он должен показать 1/3/1 и те же суммы, ZIPraw3149 / derived03149, delta0; это **ожидание, а не наблюдённый SQL-выход**.

## Восемь решений для показа

| Рабочее решение | Причина | Альтернатива / цена | Как доказать на нашем коде |
|---|---|---|---|
| 7 dims + 4 отдельных факта, натуральные ключи | Сохранить 47 бизнес-полей восьми источников и независимые grains | Нормализованный detail core тоже допустим; один плоский факт размножает суммы | CONTRACT, INSERT/FK, EXCEPT ALL mapping в90_checks; DB pending |
| Добавлен `dim_customer_context` | Buyer не задаёт единственный адрес; unused contexts тоже нельзя потерять | Держать только адрес заказа потеряет неиспользованный context; SCD без источника выдумает историю | 10_dims/20_facts; mapping всех customers; исходные6dims уточнены агентом, не новый human approval |
| Review-order пара сохраняется целиком | Один review ID относится к нескольким orders | Review entity+bridge допустим; dedup по ID теряет связи | PK пары; NULL-aware payload variants и warning конфликта; offline checks готовы |
| Children агрегируются до JOIN | Не размножать item/payment/review меры | Детальный JOIN допустим для связи, но не сумм; DISTINCT amount скрывает законные повторы | Настоящий заказ выше; CTE в40_mart; synthetic 2×2×3 |
| `item_revenue`, `order_gmv`, payment отдельно | Без доставки / с доставкой / платежи — разные компоненты и n | Один amount вводит неоднозначность; отдельные колонки требуют подписей | q03_average_order, payment coverage; обе tolerance-ветки и знаменатели |
| NULL / ноль / отсутствие строки различаются; numeric без раннего округления | Иначе фальшивое равенство и потеря precision | COALESCE всего в0 проще визуально, но меняет смысл | component counts, full vs known sums; checks NULL/0/1.234/cent boundary |
| Исходные даты и категории сохраняются | Ошибка этапа не портит весь заказ; нет перевода не значит нет категории | Удаление аномалий/INNER JOIN translations теряет данные; late weights остаются вариантами | data_issues, missing/translation flags, day/timestamp и min/max views |
| Build с явным inventory RESTRICT, одной транзакцией и checks | Ошибка не должна публиковать частичную модель | CASCADE опасен чужим зависимостям; raw pause — ручной протокол, не автоматическая защита | Wrapper/00_schemas/90_checks; синтаксис и dry-run проверены, DB rollback/concurrency pending |

Открытые бизнес-параметры не решаются на показе молчанием: counts/windows, review weights, late rules, область дашборда и окончательная рубрика. Подробности — [17 вопросов](../implementation-brief-20261028.md#все-17-вопросов). Обсуждение остаётся в родительском треде.

## Короткие ответы жюри

- **У вас модель уже работает?** Код готов и прошёл малые offline/static проверки. PostgreSQL-build и данные core ещё не проверены; фактических model answers мы не предъявляем.
- **Что именно проверено?** 14 unittest о manifest/isolation safety;93 synthetic DuckDB checks настоящих mart/answer SQL; static19; wrapper dry-run; план16 DB-кейсов. Методы различаются, число не является числом пройденных SQL runtime-кейсов.
- **Почему семь справочников, а не шесть?** Добавлен customer context для сохранности всех source customer rows и адресного контекста. Это уточнение реализации агента; buyer dim не получает «текущий адрес».
- **Откуда взялась цифра выручки?** 13 221 498.11 — контроль задания/CSV. Наш SQL рассчитывает её через core/mart; результат на PostgreSQL пока pending, поэтому не копируем контроль в колонку ответа.
- **Как уверены, что не потеряли данные?** Спроектированы проверки не только counts/sums: ключи, двусторонние EXCEPT ALL по типизированным значениям, NULL/payload/FK/calendar и компенсирующиеся ошибки. В PostgreSQL их предстоит выполнить.
- **Почему нет живой БД?** На Mac guard78 и отсутствующий Docker daemon. Обход/VM/тяжёлые установки запрещены. Показали воспроизводимые малые проверки и существующий код; SQL runtime будет отдельным evidence.
- **Доставили — значит выкупили?** Нет. Это только правило eligibility учебной выручки; выкуп, возврат и settlement требуют новых событий.
- **Что сделаете с новым вопросом?** Сначала grain/status/window/denominator, затем SQL из сохранённых деталей core, check и полный export. Непубликовавшиеся Q6–Q10 не придуманы и входят в scope.

## Следующий доказательный шаг после чекпоинта

На разрешённом существующем PostgreSQL16 endpoint, после правильной настройки libpq и выполнения raw/model pause protocol:

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host make build check answers rebuild-check
```

Это **не команда для текущего показа на заблокированном Mac**. Затем отдельно raw-input binding, pinned controls, negative fixtures, rollback/concurrency evidence и все десять результатов. Exact commands и условия — [build-runbook](../build-runbook.md) и [evidence](evidence.md#следующий-шаг). Публикация через W-01, Git не трогать.
