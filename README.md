# Capibara — от данных маркетплейса к объяснимой модели

Решение кейса RWB **«Модель маркетплейса: от корзины до выкупа»** на открытом датасете Olist: Бразилия, сентябрь 2016 — октябрь 2018, **8 CSV, 550 759 строк**. Исходный `raw` сохраняется; аналитические ответы строятся из нашей модели `core` через витрины `mart`.

**Для выступления сейчас:** [речь на две минуты и пять результатов](docs/submission/checkpoint-now.html) ([текст](docs/submission/checkpoint-now.md)). **Все детали:** [единый HTML-hub комплекта](docs/submission/index.html).

Код модели, сборки, проверок и SQL **5 из 10 вопросов** опубликован в main `aca34f5b693b794fc2a0ea8c2623293b462b6089`. Малые проверки: **14 Python + 93 DuckDB + 16/16 PostgreSQL 16 synthetic**. Полная Olist-сборка, CSV↔raw binding, контрольные ответы из модели и полный lifecycle остаются **pending**. Условия Q6–Q10 ещё не опубликованы. Это промежуточный результат, не заявление о готовности всех десяти ответов.

## Что сдаём по требованиям

| Обязательный результат | Где смотреть | Состояние |
|---|---|---|
| SQL сборки core с нуля, одним запуском | [build.sql](model/build.sql), [wrapper](scripts/build-model.sh), [runbook](docs/build-runbook.md) | Реализован; full Olist clean/rebuild pending |
| Запросы и цифры для 10 вопросов из модели | [SQL Q1–Q5](model/50_answers.sql), [RESULTS](answers/RESULTS.md), [реестр ответов](docs/submission/evidence.md#ответы-q1q10) | Q1–Q5 реализованы; full-data exports pending; Q6–Q10 ждут условий |
| Записка решений ≤½ страницы | [записка](docs/submission/decisions-note.html), [текст](docs/submission/decisions-note.md) | Подготовлена; принятый пакет отражён |
| Концепция дашборда | [пользователи, формулы, grain, источники и неаддитивность](docs/submission/dashboard-concept.md) | Подготовлена; область и HTML приняты; подключённый full-data UI pending |
| Стратегия развития | [сущности, SCD, PostgreSQL, следующий стек и риски](docs/submission/growth-strategy.md) | Подготовлена; пороги нагрузки требуют измерений |

Семь критериев PDF: ответы 30, модель 30, поддерживаемость 15, понимание и вброс 25, концепция дашборда 20, ИИ 15, развитие 20 — **155 баллов**. [Защита и репетиция](docs/submission/defense.md), [показ](docs/submission/presentation.html) и [AI evidence](docs/submission/ai-log.md) помогают предъявить результат; баллы себе не выставляем.

## От восьми CSV к модели

Порядок объяснения: [файлы и строки → связи](docs/submission/source-guide.md) → [требования организаторов](hack-context/hackathon-students/docs/handout.md) → [контракт модели](model/CONTRACT.md) → [метрики](docs/metric-definitions.md) → [проверки](docs/submission/evidence.md) → сдаваемые материалы. Нельзя подгонять детали под пять известных вопросов: модель сохраняет данные для будущего «вброса».

**7 общих справочников:** `dim_customer` (устойчивый `customer_unique_id`), `dim_customer_context` (контекст `customer_id` и адрес заказа), `dim_seller`, `dim_product`, `dim_category`, `dim_date`, `dim_order_status`.

**4 отдельных факта:**

| Факт | Одна строка и ключ |
|---|---|
| `fact_order` | Заказ: `order_id`; сохраняется и без дочерних строк |
| `fact_order_item` | Одна наблюдаемая единица товара: `(order_id, order_item_id)` |
| `fact_payment` | Один платёж: `(order_id, payment_sequential)` |
| `fact_review` | Связь отзыв–заказ с полным payload: `(review_id, order_id)` |

Реальный [CSV-заказ](docs/submission/order-example.json): **1 позиция, 3 платежа, 1 отзыв**. Цена **29.99**, доставка **8.72**, GMV и платежи **38.71**. Наивный JOIN повторит цену трижды: **89.97**. Поэтому каждый дочерний факт сначала агрегируется до нужного уровня. Этот пример прочитан из CSV; [иллюстративный SQL из core](docs/submission/order-example.sql) пока не предъявляется как выполненный full-data ответ.

## Метрики и принятые решения

| Показатель | Правило |
|---|---|
| `item_revenue` | `sum(price)` по позициям delivered, **без доставки**; право на выручку централизовано в `dim_order_status.is_revenue` |
| `order_gmv` | Сумма `price + freight_value` до уровня заказа; средний чек — среднее по delivered-заказам, не позициям |
| Покупатель | `customer_unique_id`; адрес — контекст заказа, не текущий адрес покупателя |
| Q1 | 24 календарных месяца `[2016-09-01, 2018-09-01)`, включая пустой месяц; обе именованные совокупности заказов |
| Q2 | Выручка delivered, обе именованные совокупности счётчиков; весь снимок |
| Q3–Q5 | Весь снимок; статус и знаменатель указаны у каждого показателя |
| Пропуски и качество | Нет строки, NULL и измеренный ноль различаются; аномалии помечаются без исправления догадками |

Пользователь принял раздельные факты и общие справочники, сохранение всех review-order связей, эти денежные определения и окна/совокупности Q1–Q5. Принята область дашборда **«выполнение и сервис с продажами и качеством»**, технология **HTML**. Варианты late day/timestamp, веса отзывов и smoothing остаются именованными открытыми вариантами; им не приписывается человеческое утверждение. Причины и альтернативы — в [короткой записке](docs/submission/decisions-note.md), полный пакет — в [брифе](docs/implementation-brief-20261028.md). Канон решений — [decision-log](docs/decision-log.md).

## Одна команда сборки

Нужны **уже работающий PostgreSQL 16**, `psql`, настроенный правильный endpoint/роль и загруженные восемь таблиц `raw`. Сначала владелец загрузки останавливает все raw reload/writers, дожидается текущих транзакций и подтверждает паузу на весь запуск. Переменная ниже лишь фиксирует выполненную оператором предпосылку. Сборка пересоздаёт перечисленные owned-объекты `core`/`mart` в одной транзакции и включает относительные самопроверки.

```sh
RWB_RAW_RELOAD_PAUSED=1 RWB_DB_MODE=host make build
```

Host defaults: `127.0.0.1:5432`, database `marketplace`, user `hack`; переопределение через libpq/`PGSERVICE` — в [runbook](docs/build-runbook.md). Пароль — вне Git. Для **уже запущенного** Compose PostgreSQL есть `RWB_DB_MODE=docker`. Сборка сама не запускает Docker и не загружает raw.

**`scripts/setup.sh` — подготовка/перезагрузка исходного стенда, а не ежедневная сборка модели:** он выполняет `TRUNCATE` и повторную загрузку `raw`; `--reset` удаляет volumes. Применять только к своему согласованному окружению. На текущем Mac preflight вернул **78**: тяжёлые Docker/build/полный fixture здесь не запускать и guard не обходить. Команда выше приведена для разрешённого подготовленного стенда, сейчас она нами не выполнялась. [Подготовка окружения](docs/dev-environment-20261028.md), [README организаторов](hack-context/hackathon-students/README.md).

## Что фактически проверено

| Метод | Наблюдаемый результат | Предел доказательства |
|---|---|---|
| Python unittest | 14 PASS, независимый повтор координатора | Manifest/isolation, не данные Olist в core |
| DuckDB synthetic SQL | 93 PASS, [отчёт](answers/verification.json) | Настоящие mart/answer SQL на малых данных; не PostgreSQL full build |
| PostgreSQL 16.15 synthetic | 16/16 PASS; fixture CLI 0.944 s; [отчёт и ограничения](research/implementation-review-20261028/pg-smoke.md), [JSON](research/implementation-review-20261028/pg-smoke.json) | Реальные малые PG cases; временный сервер остановлен; не полная Olist-сборка |
| Static/source и CSV | Ссылки, структура, SQL inventory, связанный заказ | Статика/CSV не доказывают равенство CSV↔raw↔core |
| Независимое Astra review | 1 P1 + 4 P2: [technical evidence](docs/submission/evidence.md#независимый-review) | Исправления ведёт координатор; готовность full model не объявлена |

Полная Olist-сборка, CSV↔live raw binding, pinned control, clean/rebuild/late rollback/concurrency и full-data exports остаются **pending**. Наличие транзакции и зелёные малые проверки не заменяют эти результаты. [Матрица приёмки](docs/submission/evidence.md#матрица-runtime-приёмки).

Малые команды из корня, без установки зависимостей и запуска БД:

```sh
python3 docs/submission/verify_pack.py
python3 answers/static-check.py
python3 scripts/verify-model.py --plan
python3 -m unittest discover -s tests/model -p 'test_*.py'
```

При уже установленном DuckDB: `python3 answers/check_offline.py` — малые synthetic SQL checks; не устанавливать пакет ради показа. `--plan` печатает план, а не выполняет 16 PG cases. Точные результаты и provenance — в [evidence](docs/submission/evidence.md).

## ИИ, защита и развитие

ИИ помогал исследовать источники, проектировать SQL, проверки и документацию. Пользователь принял конкретный пакет решений; предложения агента и неизвестное подписаны отдельно. [AI log](docs/submission/ai-log.md) связывает источник, генерацию, проверку, результат и ограничения; [review](research/implementation-review-20261028/astra-review.md) сохраняет возражения. Участники должны объяснить свой grain, ключ, JOIN и знаменатель на [репетиции](docs/submission/defense.md), а не ссылаться на авторитет модели.

Дальше — события корзины/оплаты/возвратов и выкупа, проверяемая история продавцов/товаров/адресов, затем измерение запросов и SLA. Olist delivered не доказывает финансовый выкуп; единственный снимок не восстанавливает SCD-историю. Предел PostgreSQL определяем workload/памятью/временем ответа, не выдуманным количеством строк; возможный аналитический стек и условия миграции — в [стратегии развития](docs/submission/growth-strategy.md).

## Материалы и координация

- [Материалы организаторов, read-only](hack-context/): [PDF кейса](hack-context/Кейс%20Модель%20маркетплейса.pdf), [задание](hack-context/hackathon-students/docs/handout.md), [текущие вопросы](hack-context/hackathon-students/docs/tasks.md). Обновление Q6–Q10 берём из источника организаторов, условия не придумываем.
- [Исходный профиль](docs/profiling.md), [исследования](research/README.md), [контракт модели](model/CONTRACT.md). Исходные CSV в `data/` не публикуются в Git.
- [Карта работ](docs/workstreams.md), [журнал решений](docs/decision-log.md), [идеи](docs/ideas.md), [общее объяснение](explainer.html). README и hub — навигация, не новые реестры статусов.
