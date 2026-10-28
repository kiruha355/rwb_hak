# Защита и репетиция

**Цель:** участник объясняет свой SQL, показывает проверку и предсказывает поведение на изменённом входе. Ответ из термина «звезда/SCD/идемпотентность» без нашего поля, JOIN или evidence недостаточен. Эта памятка подготовлена ИИ; живая репетиция команды пока не проведена.

**На 13:30 МСК:** открыть [короткий сценарий](checkpoint-1330.md) и [настоящий связанный заказ](order-example.json). Код 7 dims +4 facts и Q1–Q5 готов; 14/93/static19/dry-run/plan16 имеют успешный offline/static результат по повтору координатора. Отдельно W-14 выполнил16/16 малых PostgreSQL16.15 cases ([evidence](../../research/implementation-review-20261028/pg-smoke.md)); сервер остановлен. Отдельно для Q6–Q10 на PG16 проверены 16 синтетических заказов и lifecycle на 10: [протокол](../phase-20261028/evidence/pg16-small-02/summary.json). Pending относится к полному Olist lifecycle, фактическим новым full-data SQL-ответам и человеческой репетиции. При вопросе «что уже работает?» назвать конкретный малый check, а не отвечать общим «всё pending».

## Практические вопросы

| Вопрос жюри | Ответ на нашей модели / что открыть | Контрпример и граница |
|---|---|---|
| Почему buyer не customer_id? | `fact_order.customer_unique_id` и `dim_customer_context`; показать два order contexts одного buyer | Весь снимок baseline: 96 096 против 99 441; DB count ещё pending |
| Почему адрес не лежит единственным значением в dim_customer? | Адрес — наблюдаемый контекст заказа; mapping `customer_id→customer_unique_id` сохраняется | Разные адреса не доказывают переезд и не задают SCD-прошлое |
| Почему в раннем плане шесть dimensions, а теперь семь? | Добавлен `dim_customer_context`: сохраняет все source customer rows, даже неиспользованные заказами; 47 бизнес-полей имеют mapping | Это уточнение агента; семь dimensions не означают семь отдельных human approvals |
| Какая строка считается единицей? | PK `(order_id,order_item_id)` в `fact_order_item`, без выдуманной quantity | Повтор товара у того же seller — две source rows, одна группа product×seller |
| Почему review_id не PK? | `fact_review` имеет PK `(review_id,order_id)`, весь payload на паре | Один ID в двух orders нельзя удалить DISTINCT; конфликт payload нельзя скрыть latest |
| Как не потеряны заказы без items? | INSERT orders независимо; order mart LEFT JOIN агрегированных children | INNER JOIN items потеряет baseline 775 заказов; actual check нужен по множествам ключей |
| Почему суммы нельзя проверить одним JOIN? | Открыть независимые item/payment/review aggregates до order join | 2×2×3 даёт 12 rows; DISTINCT amount уничтожит одинаковые законные суммы |
| Чем выручка отличается от чека? | Eligibility в `dim_order_status.is_revenue`; item price против order sum(price+freight) | Revenue не payment и не прибыль; average item не average order |
| Что с новым статусом? | По контракту сохраняется в status domain, `is_revenue=false`, warning на unexpected status | Это техническая безопасная политика, не присвоенный новый бизнес-смысл |
| Почему ноябрь 2016 есть? | Месяцы из DISTINCT `dim_date.month_start` и LEFT JOIN monthly aggregates | Проверить gap отдельно от duplicates; множество дней 1/3 января уникально, но неполно |
| Почему два числа заказов в Q1/Q2? | Placed/delivered именованы, supplier counts только по его items | Revenue-population не определяет смысл соседнего count; пользователь принял обе именованные populations; это не утверждение единственного смысла organiser wording |
| Можно сложить заказы продавцов? | Пересчитать distinct order IDs на объединении | Один order с двумя sellers входит в две группы; это не два orders площадки |
| Можно сложить покупателей по месяцам? | Нет; `count(distinct customer_unique_id)` по объединённому окну | Один buyer в январе и феврале — один за два месяца |
| Что с нулём и NULL? | Число children, число непустых price/freight/payment и суммы отдельно | Нет payment, all NULL payment_value и value=0 — три состояния |
| Как сводите платежи? | Item и payment totals независимо; сначала coverage, потом signed/absolute delta | Exact и >0.01 имеют разные count/sum. На baseline 639/−1819.51 vs366/−1818.84 |
| Почему numeric без раннего scale? | Показать тип numeric в контракте и input validation перед cast | Значение 1.234 не должно молча округлиться в numeric(p,2); policy должна быть проверена |
| Что с категорией без перевода? | Product→`category_key='pt:'||name`; missing translation не unknown | Unknown key `'unknown'` только при отсутствующей категории; перевод необязателен |
| Исправляете даты? | Сохраняем timestamp, аномалии/пригодность отдельно по паре дат | Carrier<purchase исключает этот интервал, не цену заказа и не все остальные интервалы |
| Поздняя доставка означает вину перевозчика? | Нет; carrier date на order, deadline на item; late day/timestamp и min/max отдельно | Нет shipment events или причины; зависимость review/late не causal effect |
| Какая средняя оценка «правильная»? | Pair/ID/order — разные веса, n и coverage видимы | Повтор ID, несколько reviews order, multi-seller order; latest не равно актуальное мнение |
| Как доказана повторяемость? | Нужны два run на одном input manifest и key/value/metric equality | Наличие DROP/CREATE не proof; техническое время меняется отдельно |
| Что при ошибке в конце сборки? | Проверить ненулевой exit, отсутствие частичного core/mart, неизменность raw | Check-results внутри транзакции откатится; нужен stderr/отдельный check-run |
| REPEATABLE READ защищает от reload raw? | Сам по себе нет; показать принятый loader/build protocol и concurrency evidence | TRUNCATE не MVCC-safe; lock rights/timeout и оба порядка запуска проверяются отдельно |
| Как отвечаете на новый вопрос? | Выбрать grain→population/window→поля core→SQL→checks→export | Не считать из raw ради готовой цифры, не менять raw для подгонки |
| Где предел PostgreSQL? | Нет измеренного универсального предела; показать workload/SLA/TCO и parity/rollback | Миллионы строк без bytes/concurrency/IO/SLA не обосновывают миграцию |
| Что сделал ИИ, что проверили люди? | [AI log](ai-log.md): источник, предложение, метод проверки и неизвестное | Согласие агентов не human approval; живая репетиция и full Olist DB run pending; малые PG16 cases16/16 PASS |


## Вопросы по блоку Б и истории

| Вопрос | Что объяснить | Контрпример и ограничение |
|---|---|---|
| Какие деньги считаются? | Item price даёт revenue; price + freight на заказ — GMV; сумма payment records — отдельный показатель. | Несколько платежей на заказ; расхождение totals не исчезает от JOIN. Payment timestamp и ledger отсутствуют. |
| Q6: цена менялась когда? | Дата покупки × наблюдавшаяся цена позиции; все лидеры по числу различных известных цен. | Продажи одного дня по разным ценам не доказывают последовательность смен каталожной цены. |
| Q7: кто входит в 500? | Порог по числу заказов выбранной популяции до фильтра дат; длительность и late имеют разные знаменатели. | Ровно 500 входит; пропущенную дату нельзя считать своевременной. Календарный день и timestamp могут расходиться. |
| Q8 — воронка? | Доли текущих статусов от всех заказов и отдельное число заказов без позиций. | Снимок не содержит переходов и не даёт конверсию между стадиями. |
| Q9 — срок рассрочки? | Среднее исходного числа частей на платёж, не срок в месяцах. 2018 — год покупки заказа, не известная дата платежа. | Заказ с несколькими платежами имеет несколько наблюдений; один payment нельзя умножать на items. |
| Q10: сколько заказов в каждой оценке? | `within_score` считает заказ раз в каждой его оценке; `single_score_only` исключает разные оценки одного заказа. Показать coverage. | Сумма групп первого варианта может превышать число уникальных заказов; связь оценки с доставкой не доказывает причину. |
| Можно восстановить старую категорию? | Имеющийся снимок её не содержит. Предлагаем версии и закрепление за выпуском/позицией, оригинал и отдельный restatement. | История и её regression ещё в работе; не обещать наблюдение прошлого из SCD, не объявлять проект реализованным. |
| Переезд покупателя? | Адрес сохраняется как контекст конкретного заказа; buyer ID связывает заказы. | Это не дата переезда; адресный regression pending. |

## Короткие запросы для объяснения кода

Это **подготовленные read-only запросы**, они не выполнялись W-12. До защиты сверить с финальными answer/check SQL владельцев; основным доказательством служат именно их опубликованные файлы и run, а не эта шпаргалка.

Реальные места для показа: [ключи и FK](../../model/20_facts.sql); [независимые items/payments/reviews CTE и coverage](../../model/40_mart.sql); [Q3 и отдельные знаменатели](../../model/50_answers.sql); [EXCEPT ALL mapping и календарные gaps](../../model/90_checks.sql); [single-transaction wrapper](../../scripts/build-model.sh). Результаты из модели и limits владельца — [answers/RESULTS.md](../../answers/RESULTS.md).

Buyer population:

```sql
SELECT count(DISTINCT customer_id) AS contexts,
       count(DISTINCT customer_unique_id) AS buyers
FROM core.fact_order;
```

Кратность детей без их совместного соединения:

```sql
WITH i AS (
  SELECT order_id, count(*) AS n FROM core.fact_order_item GROUP BY order_id
), p AS (
  SELECT order_id, count(*) AS n FROM core.fact_payment GROUP BY order_id
), r AS (
  SELECT order_id, count(*) AS n FROM core.fact_review GROUP BY order_id
)
SELECT o.order_id, i.n AS item_rows, p.n AS payment_rows, r.n AS review_pairs
FROM core.fact_order o
LEFT JOIN i USING (order_id)
LEFT JOIN p USING (order_id)
LEFT JOIN r USING (order_id)
WHERE i.n > 1 OR p.n > 1 OR r.n > 1
ORDER BY o.order_id
LIMIT 5;
```

Повтор review ID без потери пар:

```sql
SELECT review_id, count(*) AS order_associations
FROM core.fact_review
GROUP BY review_id
HAVING count(*) > 1
ORDER BY review_id
LIMIT 5;
```

## Репетиция на нашем коде

Роли A/B/C распределяет команда перед прогоном; имена людей здесь не назначены. Каждый участник проходит все четыре навыка: ключ, JOIN/grain, метрика, проверка. Объяснять можно по-русски с открытым SQL; заучивать определения не требуется.

| Раунд | Задание | Признак готовности | Фактический результат |
|---|---|---|---|
| 1 · 3 мин | A: buyer key; B: review key; C: source row | Находит PK/FK/поле в реальном файле и предсказывает duplicate/missing case | pending: не проведено |
| 2 · 3 мин | Каждый объясняет одну независимую child aggregation | Показывает grain до/после JOIN и откуда берётся сумма | pending |
| 3 · 3 мин | Каждый объясняет Q1/Q3/Q4 по SQL и export | Называет status/window/components/denominator и метод проверки | pending: DB export |
| 4 · 3 мин | Каждый разбирает no child/NULL/0 и один failing check | Показывает ожидаемый error/warning и сохранённое evidence | pending: runtime checks |
| 5 · 5 мин | Полный показ + вопрос без подготовки | Укладывается в реальный регламент; не подменяет baseline моделью | pending |

После раунда записать здесь либо в согласованном evidence: UTC, участник, конкретный вопрос, файл/строки, где запнулся, исправление, повторный результат и длительность. Не писать «репетиция PASS» по наличию этого плана.

## Упражнение со вбросом

Это наши упражнения; опубликованные вопросы организаторов и SQL разобраны в [блоке Б](block-b.md).

1. Прислали payment с NULL value и другой payment=0. Покажите, почему coverage и delta различаются; ничего не правьте в raw.
2. Один review ID связан с двумя orders с разными текстами. Покажите сохранность пар и почему единый review mean требует политики конфликта.
3. Новый статус и новый seller без перевода категории. Найдите соответствующие warnings и проверьте, что продажи/связи не исчезли.
4. Попросили средний чек выбранных продавцов. Уточните: полный чек orders с их участием или только выбранные items; подпишите оба, не распределяйте payments молча.
5. Попросили возвраты или выкуп. Покажите отсутствие события в восьми источниках и предложите минимальный source contract; не объявляйте delivered выкупом.

Для Q6–Q10 SQL и именованные варианты уже есть: показать [блок Б](block-b.md), объяснить grain, population, знаменатели и исключения, затем выполнить full-data запросы на разрешённом стенде и сохранить evidence. Человеческая репетиция и итоговые числа ещё pending.
