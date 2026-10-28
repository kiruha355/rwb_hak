# Паспорта метрик Capibara

W-10 · implementation default, не отдельное human approval. Входы:
`main@1939068295d7203a15cbb0a1ab5d407caca90f58`, research
`72c1fb6ffe43e95b2ba539dc1b396374f4bfde3a` и
[implementation brief](implementation-brief-20261028.md).
SQL-паспорта публикуются сборкой в `mart.metric_definitions`.
Источники расчёта — только `core` и производные `mart`; CSV-контроли
хранятся отдельно в `answers/control.sql` и не заполняют ответы.

## Общие правила

- Покупатель — `customer_unique_id`; заказ — `order_id`; единица товара —
  `(order_id, order_item_id)`. Колонки quantity в источнике нет.
- Правило выручки читается из `core.dim_order_status.is_revenue`;
  `mart.is_delivered` вычисляется как `order_status = 'delivered'`.
  Сейчас оба признака относятся к delivered,
  но значения и названия метрик различаются. Delivered не доказывает выкуп.
- Q1 использует дату оформления и полуоткрытое окно
  `[2016-09-01, 2018-09-01)`. Q2–Q5 — весь загруженный снимок.
  Q4 дополнительно показывает вариант с окном Q1. Это разные populations,
  а не две оценки одного и того же знаменателя.
- Timestamp источника не имеет часового пояса. Его нельзя выдавать за UTC;
  календарный день берётся без конвертации. Граница снимка не доказывает
  полноту наблюдения и не служит датой censoring для retention.
- Items, payments, reviews сначала агрегируются независимо до заказа.
  `v_orders` имеет один ряд на заказ; `v_order_items` — один ряд на item key.
  Метрики заказа нельзя суммировать после размножения на позиции.
- Денежные вычисления выполняются в numeric, округление — только в итоговой
  колонке для показа. Валюта — BRL по контексту Olist, без пересчёта курсов.
- Ноль строк ребёнка даёт 0 в **count**, но NULL в его денежной сумме.
  All-NULL и частично заполненные суммы тоже NULL в строгой метрике.
  Отдельные `*_known_sum` сохраняют сумму известных компонентов и их counts.
  У календарного месяца без заказов counts и выручка равны 0: отсутствие
  событий в этом месяце установлено, это не пропущенная цена.
- Средние, доли, distinct и оценки пересчитываются из компонентов при смене
  среза. Нельзя складывать месячные distinct покупателей, distinct заказов
  продавцов и категорий, средние чеки или проценты. Выручка и единицы аддитивны
  только по непересекающимся множествам позиций одной population.

## Q1–Q5

| Имя | Grain и формула | Статусы / время / окно | Знаменатель и NULL | Единицы / аддитивность |
|---|---|---|---|---|
| `orders_placed` | заказ; count(order_id) | все; purchase timestamp; окно Q1 | знаменателя нет; пустой месяц 0 | заказы; аддитивно по непересекающимся месяцам |
| `orders_delivered` | заказ; count с is_delivered | delivered; группировка по **месяцу покупки**, не вручения; окно Q1 | пустой месяц 0 | заказы; то же |
| `item_revenue` | позиция; sum(price) | is_revenue; purchase timestamp; Q1 окно, Q2/Q5 весь снимок | NULL если в выбранной непустой population есть неизвестная price; coverage отдельно | BRL без доставки; аддитивно по позициям |
| `seller_orders_delivered` | продавец × distinct order_id | is_delivered; весь снимок | каждый order считается один раз у каждого своего seller | заказы; не складывать по продавцам |
| `seller_units_delivered` | продавец × item key; count(*) | is_delivered; весь снимок | 0 при отсутствии позиций | единицы; аддитивно |
| `seller_orders_all_statuses` | продавец × distinct order_id | все; весь снимок | отдельно от delivered counts | заказы; не складывать по продавцам |
| `seller_units_all_statuses` | продавец × item key | все; весь снимок | count(*) | единицы; аддитивно |
| `order_gmv` | заказ; sum(price + freight_value) | все на уровне заказа; Q3 только is_delivered; весь снимок | только непустые orders с обеими компонентами у всех items | BRL с доставкой; аддитивно по заказам |
| `avg_order_gmv` | заказ; sum(order_gmv)/n_order_gmv | is_delivered; весь снимок | n_order_gmv = count непустых, полностью известных order_gmv; n_delivered и excluded отдельно | BRL/заказ; неаддитивно |
| `avg_payment_amount` | заказ; sum(payment_amount)/n_payment_amount | is_delivered; весь снимок | свой n: orders с непустыми полностью известными payments; не знаменатель GMV | BRL/заказ; неаддитивно |
| `avg_source_rows` | заказ; avg(source_rows_count) | is_delivered; весь снимок | все delivered orders, в том числе 0 items | строк/заказ; неаддитивно |
| `avg_units` | заказ; avg(units_count) | is_delivered; весь снимок | тот же n; строка = единица | единиц/заказ; неаддитивно |
| `avg_distinct_product_seller_lines` | заказ; avg(count distinct(product_id,seller_id)) | is_delivered; весь снимок | тот же n; это **не** число исходных строк | групп/заказ; неаддитивно |
| `buyers_all_snapshot` | покупатель; count distinct customer_unique_id | все; весь снимок | наблюдённые buyers; не все люди за пределами снимка | покупатели; distinct неаддитивен |
| `repeat_buyers_all_snapshot` | покупатель с count(order_id)>1 | все; весь снимок | абсолютное число, не число повторных заказов | покупатели; неаддитивно |
| `repeat_buyer_pct_all_snapshot` | 100 × repeat_buyers / buyers | все; весь снимок | buyers, при 0 buyers результат NULL | %; неаддитивно |
| `buyers_q1_window`, `repeat_buyers_q1_window`, `repeat_buyer_pct_q1_window` | те же формулы, группировка выполняется **после** фильтра окна | все; purchase timestamp; окно Q1 | повторным считается buyer с >1 заказом **в этом окне**; не retention | buyers / %; неаддитивно |
| `category_item_revenue` | категория позиции; sum(price) | is_revenue; весь снимок | сохраняются все category members; missing category ≠ missing translation | BRL; аддитивно по категориям позиций |
| `category_revenue_pct` | 100 × category_item_revenue / общий item_revenue той же population | is_revenue; весь снимок | общий знаменатель NULL, если у любой категории price неполна; 0 denominator → NULL | %; доли нельзя суммировать вне одной исчерпывающей классификации |

`avg_source_rows` и `avg_units` ожидаются около 1.142, а отдельное
`avg_distinct_product_seller_lines` — около 1.039 **в CSV reference**.
Это не результаты выполнения core. Q2 возвращает delivered revenue и counts
рядом; all-status counts имеют отдельные имена. Q5 оставляет `is_unknown`,
`is_translated` и португальское имя: две известные категории без перевода
не превращаются в категорию «без категории».

## Платёжная сверка

`mart.v_order_payment_reconciliation` — один заказ;
`mart.v_payment_reconciliation` — статус × покрытие. Поле `payment_coverage`
принимает ровно `both`, `items_only`, `payments_only`, `neither` и зависит от
наличия строк, а не от нулевой суммы. Counts наличия и полноты независимы:
`source_rows_count`, `price_valid_count`, `freight_valid_count`,
`item_components_valid_count`, `payments_count`, `payment_valid_count`.

Денежный comparator: `payment_delta = payment_amount - order_gmv` только если
обе стороны присутствуют и все денежные компоненты известны. Иначе NULL.
`delta_nonzero_exact` — Δ <> 0; `delta_gt_001` — abs(Δ) > 0.01;
`delta_eq_001` — abs(Δ) = 0.01. Никакого предварительного округления.
Для каждого predicate отдельно выводятся order count, signed sum(Δ) и
absolute sum(abs(Δ)). Общий net не является объёмом расхождений.
Пустая группа predicate даёт 0 расхождений и 0 суммы; наличие неприменимых
заказов видно по `comparable_orders` и `non_comparable_orders`.

Coverage-суммы — суммы **известных** order totals с собственным числом
известных/неизвестных orders, а не обещание полного денежного итога.
Валидная денежная компонента означает non-NULL numeric после типовых
проверок core, не положительное значение: ноль и отрицательные суммы сохраняются.
Ваучеры, рассрочка, скидки и возвраты не объявляются причинами расхождений.
Строки payment и installments не являются графиком dated cash-flow events.

## Отзывы

`mart.v_review_payload_variants` сохраняет каждый различный payload внутри
review_id и его association count; GROUP BY включает NULL как отдельное
значение. `mart.v_review` имеет один ряд на ID, но payload заполняется только
при **одном** варианте. При конфликте `has_payload_conflict=true`, payload
NULL, варианты остаются доступны. Произвольного first/latest/min payload нет.

`mart.v_review_weighting` показывает три именованных равноправных варианта:

| weight_basis | Единица веса | numerator / denominator / NULL |
|---|---|---|
| `review_order_pair` | связь review_id–order_id | sum(score) / count(score), все сохранённые пары |
| `review_id_unambiguous_payload` | review_id | sum(score) / count(score), конфликтные IDs исключены с отдельным count |
| `order_mean_of_review_pairs` | заказ | sum(средняя score пар заказа) / число orders с известной оценкой |

Оценки используют все статусы, весь снимок, без привязки к месяцу покупки.
Orders без review не становятся score=0; missing scores не становятся нулём.
Для всех вариантов выводятся числитель, знаменатель и исключённые единицы.
Это описательная связь, без причинных выводов и без распределения score на
items/sellers. Единственный вес не выбран молчанием.

## Календарные варианты выполнения

Если используются `mart.v_order_delivery_variants`, имена фиксируют правило:
`is_late_calendar_day` сравнивает даты вручения и обещания;
`is_late_timestamp` — полные timestamps. Оба применимы только к delivered
с двумя датами. Одинаковый день 18:00 > 00:00 даёт разные ответы.
`is_handover_after_min_item_deadline` и
`is_handover_after_max_item_deadline` сравнивают timestamp передачи **заказа**
с min/max item shipping limit отдельно, только при полном покрытии deadlines.
Они не доказывают время передачи каждой позиции или вину участника.
Отрицательный интервал исключает только метрику этой пары дат.
Варианты не объявляются согласованным единственным late rule.

`purchase_to_delivery_days`, `purchase_to_carrier_days`,
`carrier_to_delivery_days` — elapsed seconds / 86 400, с дробными днями.
Первые и последние — delivered с известной неотрицательной соответствующей
парой timestamp; purchase→carrier — все статусы с такой парой.
Знаменатель среднего — только orders с известным значением **этого**
интервала; средние не складываются. Показатели не оценивают ненаблюдённые
будущие события и не устанавливают причин задержки.

## Результаты и ещё не опубликованные вопросы

[RESULTS](../answers/RESULTS.md) начинается со статуса
`not executed from core`. Runtime, rollback, повторная сборка и DB controls
остаются pending до подходящего PostgreSQL 16 стенда. Проверка парсером или
малой offline fixture не заменяет выполнение PostgreSQL.
Q6–Q10 не выдумываются: ожидается обновление
`hack-context/hackathon-students/docs/tasks.md`, затем паспорта, SQL и
регрессия Q1–Q5. Контрольные цифры не используются как строки ответов.
