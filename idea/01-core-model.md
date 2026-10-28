# Модель core: принципы и черновик таблиц

**Статус:** 💡 черновик · **Дата:** 2026-10-28 · **Приоритет:** обязательно, делаем первым

## Зачем
За модель дают 30 (качество) + 15 (поддерживаемость) + 25 (понимание) баллов,
и на ней же держатся ответы (30). Всё остальное строится поверх.

## Принципы (договорённость команды)
1. **Правильное зерно.** Для каждой таблицы одна фраза: «одна строка = …». Это главное место, где все ошибаются: средний чек считается по заказам, выручка продавца — по позициям.
2. **Правильные ключи.** PK и FK объявлены в базе, тогда база сама не пустит дубль или сироту.
3. **Бизнес-правила в одном месте.** Правило «статус даёт выручку» задаётся в справочнике `dim_order_status` (предложение из `AGENTS.md`), а флаг `is_revenue` в `fact_order` выводится из него. Все запросы берут выручку оттуда и не решают каждый раз заново, какие статусы считать.
4. **Честная обработка грязи.** Пустая категория превращается в `unknown`, а не теряется. Месяц без заказов есть в календаре. Дубли отзывов разобраны, и решение записано.
5. **Самопроверки.** После сборки скрипт сам проверяет, например: строк в `fact_order` столько же, сколько в `raw.orders`; сумма по категориям равна общей выручке; нет позиций без товара. Если что-то не так — ошибка.
6. **Готовые поля для анализа.** `delivery_days`, `is_late`, `is_repeat_customer` и т. п. Тогда новые вопросы после вброса решаются за минуты.

Черновик звезды в `AGENTS.md` (в `main`) по сути совпадает с этим. Здесь он
детализирован: зерно, поля, проверки.

## Черновик таблиц (обсуждаем, не финал)

### Справочники
| Таблица | Одна строка = | Ключ | Из raw | Заметки |
|---|---|---|---|---|
| `dim_date` | один календарный день | `date_key date` | генерируется | 2016-09-01 … 2018-10-31; поля month, year, quarter, day_of_week, is_weekend. Месяц без заказов появится автоматически |
| `dim_customer` | один реальный покупатель | `customer_unique_id` | customers | first_order_at, orders_count, is_repeat_customer. Адрес не храним: он меняется (см. findings) |
| `map_customer_order` или поле в `fact_order` | связь `customer_id` → `customer_unique_id` | `customer_id` | customers | возможно, достаточно колонки в `fact_order` |
| `dim_order_status` | один статус заказа | `order_status` | orders (8 значений) | `is_revenue` (сейчас true только у `delivered`), `is_final`, `is_canceled`, описание по-русски. Единственное место правила выручки |
| `dim_seller` | один продавец | `seller_id` | sellers | city (как пришло), `city_clean` (города грязные: `sp / sp`, `pinhais/pr`, email, цифры), state, zip_prefix |
| `dim_category` | одна категория товара | `category_id` (суррогат) или `category_name_pt` | translation + products | строка `unknown` для пустых; 2 категории без перевода — english = NULL или = pt (решить) |
| `dim_product` | одна карточка товара | `product_id` | products | FK на `dim_category`, NOT NULL (пустые → `unknown`); исправить `lenght` → `length`; вес: 2 NULL и 4 нуля → NULL + флаг |

### Факты
| Таблица | Одна строка = | Ключ | Из raw | Ключевые поля |
|---|---|---|---|---|
| `fact_order` | один заказ | `order_id` | orders + агрегаты | customer_unique_id, customer_id, адрес-снимок (zip/city/state), status (FK на `dim_order_status`), все 5 timestamp, `is_revenue` (из `dim_order_status`), `is_delivered`, `is_canceled`, units_count (строк `order_items`), distinct_products_count, sellers_count, `item_revenue` (Σprice), `freight_amount`, `order_gmv` (Σprice + Σfreight), `payment_amount`, `has_payment_mismatch`, `has_timeline_anomaly`, `delivery_days`, `is_late` (оба NULL при аномалии дат), `customer_order_seq`, `review_score` (по политике) |
| `fact_order_item` | одна единица товара одного продавца в заказе | (`order_id`, `order_item_id`) | order_items | product_id, seller_id, price, freight_value, shipping_limit_date, `shipped_late` (carrier_date > shipping_limit) |
| `fact_payment` | один платёж по заказу | (`order_id`, `payment_sequential`) | order_payments | payment_type, installments, value; флаги аномалий (0, `not_defined`) |
| `fact_review` | один отзыв о заказе | (`review_id`, `order_id`) | order_reviews | score, has_comment, creation_date, answer_ts; `is_latest_for_order` |

Строки `raw.orders` без позиций (775) остаются в `fact_order` с нулевыми суммами.
Это решение нужно записать в записку.

Названия денежных полей `item_revenue` и `order_gmv` взяты из `AGENTS.md`, чтобы
«выручка без доставки» и «чек с доставкой» не путались.

**Аномалии дат** (`docs/profiling.md`): 166 заказов переданы в доставку раньше покупки,
у 23 вручение раньше передачи, у 6 недоставленных есть дата вручения. Строки не
удаляем, ставим `has_timeline_anomaly = true` и не считаем по ним длительности.

### Что дальше в mart
- `mart.v_revenue_monthly`, `mart.v_seller_revenue`, `mart.v_category_revenue`, `mart.v_avg_check`, `mart.v_customers` — по одному view на вопрос.
- Метрики считаются только из `core` через флаги, без повторной логики статусов.

## Самопроверки (минимальный набор)
- [ ] `count(fact_order) = count(raw.orders)`; то же для items, payments, reviews.
- [ ] Нет NULL в FK; FK объявлены (проверит сама база).
- [ ] Σ выручки по категориям = Σ выручки по месяцам = Σ по продавцам = 13 221 498.11.
- [ ] `fact_order.item_revenue` = Σ`fact_order_item.price` по заказу.
- [ ] Число покупателей = 96 096.
- [ ] Каждый месяц периода есть в `dim_date`.
- [ ] Каждый статус из `fact_order` есть в `dim_order_status` (проверит FK).
- Реализация: проверки отдельным скриптом `model/99_checks.sql`, как договорено в `AGENTS.md`. Скрипт пишет результат в таблицу `core.check_results` (имя проверки, ожидание, факт, ok) и в конце падает через `RAISE EXCEPTION`, если есть хоть одна неудача. Таблицу же можно показывать на карте DWH (см. `03-dwh-map.md`).

## Открытые вопросы
- [ ] Суррогатные ключи (int) или натуральные (md5-строки)? Натуральные проще объяснить, суррогатные легче и быстрее. Для хакатона склоняемся к натуральным с объяснением.
- [ ] Отзывы: какой отзыв считать «оценкой заказа» при дублях.
- [ ] Адрес: снимок в `fact_order` (склоняемся) или SCD2 в `dim_customer`.
- [ ] «Строка» против «единицы» в вопросе 3 (см. AGENT_BRIEF.md §5): на доставленных заказах 1.142 строк (единиц) и 1.039 уникальных товаров. В `fact_order` храним оба поля, а ответ согласуем с командой.
- [ ] Структура файлов: один `model/build.sql` или `model/01_dims.sql`, `02_facts.sql`, `99_checks.sql` + `model/build.sh`.

## Решение
_пока нет_
