# API Q6–Q10

- Owner: implementation sub-agent, Codex / GPT-6.1 Sol; checkout
  `/Users/a/.t3/worktrees/rwb_hak/t3-1b244690`.
- Coordinator: `mcp:ff50ef29-ba22-48ce-836b-d046b08d3a24`.
- Input: `aab62d7a59f196be051df12466fb21c0da4659b9`, опубликованная
  `t3/integrate-q6-q10-marts`; исходный main snapshot
  `bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4`.
- Совместимость: точный diff `bbbfab8..6452806eae21d13126da9de8ebaba01a2152eaea`
  прочитан после fetch. Это новая реализация коллеги, сохранённая через адаптер.
- Proposal branch: `t3/api-answers-block-b-aab`; без merge main, PR и deploy.
- Owned: `app/api/block-b.js`, маленькое подключение в `app/api/server.js`,
  `app/api/tests/block-b*`, этот документ. Общий registry не редактировался.
- Ownership записан до правок API: `2026-10-28T14:04:40Z`.
- UTC проверки: `2026-10-28T14:17:22Z`; status: `ready_for_integration`;
  проверки и ограничения ниже.

Основные источники: локальные требования организаторов `558f0f6`,
`AGENTS.md`, `README.md`, `FRONTEND-HANDOFF.md` на input, исходники stage 55
и фактическое исполнение. Веб, реальные CSV и рабочая БД в этой задаче не
использовались. Новых approvals определений метрик нет: именованные варианты
остаются вариантами, выбор переключателя в UI не становится общим решением.

## Совместимость с main 6452806

В diff коллеги: новый `/api/answers-b` (+24 строки `server.js`),
`AnswersB.tsx` (+152 строки), переключение блоков в `Answers.tsx`, подпись
пункта в `DataPage.tsx`. UI читает массивы `q6`, `q7`, `q8`, объект `q9`,
`q10.rows/coverage`, флаг `available`. `useApi` читает JSON ошибки при HTTP
не 2xx. Он не добавляет глобальные фильтры к URL этого запроса.

Существующая страница и её подключение не изменены; второй страницы нет.
Inline-запросы `/api/answers-b` заменены одним подключением общего reader:

```diff
 import pg from "pg";
+import { mountAnswersBlockB } from "./block-b.js";
 ...
-// inline app.get("/api/answers-b", cached(... seven SELECTs ...))
+mountAnswersBlockB(app, { q, cached });
```

`/api/answers-b` сохраняет успешную форму, все прежние поля, `available: true`
и группы Q7 ниже 500: страница использует их для счётчика не прошедших порог
штатов. Дополнительно возвращаются недостающие поля stage 55 и `meta`.
При отсутствии схемы теперь HTTP 500 с `error`, который существующий `useApi`
передаёт в `ErrorBox`. Успешный `{available:false}` больше не маскирует отказ.

Согласованный `/api/answers-block-b` — адаптер той же реализации с
`q6.rows/q7.rows/q8.rows`; Q7 в нём сразу ограничен `orders_count >= 500`.
Дополнительный маршрут сохраняет уже согласованный контракт без изменения
массивов, используемых страницей коллеги. Цена совместимости — два URL и
отдельные записи существующего cache; SQL и определения общие. Нет двух
зарегистрированных обработчиков одного URL.

`/api/answers` Q1–Q5, `q`, cache TTL 10 минут, cache-clear и pg parsers
сохранены. В production используются только установленные зависимости API,
новых зависимостей нет. API читает те же семь views, без повторной реализации
их расчётов в JS; numeric/bigint идут как number, date — как строка через
существующие parsers. NULL передаётся без преобразования и округления.

## Mount и HTTP

В `server.js` после определения `q`, `cached` и текущих маршрутов, перед listen:

```js
import { mountAnswersBlockB } from "./block-b.js";
// ... existing q, cached, routes
mountAnswersBlockB(app, { q, cached });
```

| Маршрут / статус | Ответ |
|---|---|
| `GET /api/answers-block-b`, 200 | `BlockBResponse` ниже |
| `GET /api/answers-b`, 200 | `LegacyBlockBResponse`, совместимый со страницей коллеги |
| Оба маршрута, 400 | `{error: string, code: "invalid_block_b_filter"}` |
| Оба маршрута, 500 | `{error: string}` при missing view/column, timeout, connection и других ошибках БД |

Все семь чтений должны завершиться успешно. Ошибка не возвращает частичный
ответ, не заменяется пустыми массивами и не кэшируется. Настоящий пустой
результат SELECT остаётся 200 с metadata. Кэш ранее успешного ответа живёт по
прежнему TTL; отдельного freshness/E2E обещания нет.

## Фильтры и scope

По умолчанию возвращаются все именованные варианты, без назначения единого
одобренного набора. Допустимы только одиночные строковые параметры:

| Параметр | Enum | Какие части ответа фильтрует |
|---|---|---|
| `population` | `all_statuses`, `delivered` | Q6, Q7, Q10 rows и coverage |
| `late_basis` | `calendar_day`, `timestamp` | Q7, Q10 rows |
| `score_policy` | `within_score`, `single_score_only` | Только Q10 rows |
| `period` | `all_snapshot`, `purchase_2018` | Только Q9 methods |

Пример: `/api/answers-block-b?population=delivered&late_basis=calendar_day&score_policy=single_score_only&period=purchase_2018`.
Он возвращает пять Q10 rows и одну coverage row. Q8 и Q9 states не меняются;
Q9 states всегда относится к покупкам заказов в 2018, всем статусам. Coverage
имеет grain population, без score policy и late basis. Клиентам с независимыми
переключателями по вопросам подходит ответ без параметров и локальный выбор
серий, как у существующей страницы.

Неизвестные ключи, повторные параметры/массивы, объекты, пустые строки,
неверный регистр, произвольные значения и SQL payload дают 400 **до q и cache**.
`from`, `to`, `state`, `category`, `min_orders`, `limit` не поддерживаются.
Это снимок, Q9 — фиксированное окно/именованные окна; период и категория
не вычисляются заново поверх агрегатов. Q6 сохраняет глобальных лидеров,
включая всех при равенстве; фильтра истории после выбора лидера по периоду нет.
SQL неизменен между вариантами, все значения передаются placeholders.
Порог 500 задан сервером по заданию; в URL его менять нельзя.

`meta.scope`:

```json
{
  "q6": "all_snapshot",
  "q7": "all_snapshot",
  "q8": "all_snapshot",
  "q9_states": "purchase_2018",
  "q9_methods": "named_periods",
  "q10": "all_snapshot",
  "q7_min_orders": 500,
  "unsupported_filters": ["from", "to", "state", "category"]
}
```

У `/api/answers-b` `q7_min_orders: null`: порог применяет существующий UI,
а endpoint сохраняет группы ниже него. `meta.variants` перечисляет четыре
allowlist enum, `meta.filters` содержит все четыре ключа и строку выбранного
варианта либо null, означающий «все варианты», а не неизвестное значение строки.

## Типы JSON

Поля строк ровно соответствуют `model/55_answers_block_b.sql` input; API их не
переименовывает. Дни — дробные сутки, проценты 0–100. Нет преобразования числа
частей платежа в месяцы. `orders_count` не заменяет duration/late denominators.

```ts
type Population = "all_statuses" | "delivered";
type LateBasis = "calendar_day" | "timestamp";
type ScorePolicy = "within_score" | "single_score_only";
type Period = "all_snapshot" | "purchase_2018";

type Q6 = {
  population: Population; product_id: string; distinct_prices: number;
  units_with_unknown_price: number;
  purchase_date: string | null; // YYYY-MM-DD, no timezone conversion
  price: number | null; units_sold: number;
};
type DeliveryStats = {
  orders_count: number; duration_denominator: number;
  avg_delivery_days: number | null;
  late_denominator: number; late_orders: number; late_pct: number | null;
};
type Q7 = DeliveryStats & {
  population: Population; customer_state: string | null; late_basis: LateBasis;
};
type Q8 = {
  order_status: string; orders_count: number; orders_pct: number;
  orders_without_items: number;
};
type Q9State = {
  customer_state: string | null; payment_count: number; amount_denominator: number;
  payment_amount: number | null; known_payment_amount_sum: number | null;
  installments_denominator: number; avg_installments_all_types: number | null;
  credit_installments_denominator: number; avg_installments_credit_card: number | null;
};
type Q9Method = {
  period: Period; payment_type: string | null; payment_count: number;
  installments_denominator: number; avg_installments: number | null;
};
type Q10 = DeliveryStats & {
  population: Population; score_policy: ScorePolicy; late_basis: LateBasis;
  review_score: 1 | 2 | 3 | 4 | 5;
};
type Q10Coverage = {
  population: Population; orders_count: number; orders_without_score: number;
  orders_with_multiple_scores: number; orders_in_multiple_valid_score_groups: number;
  orders_with_out_of_range_score: number;
};
type BlockBMeta = {
  scope: {
    q6: "all_snapshot"; q7: "all_snapshot"; q8: "all_snapshot";
    q9_states: "purchase_2018"; q9_methods: "named_periods"; q10: "all_snapshot";
    q7_min_orders: 500 | null; unsupported_filters: string[];
  };
  variants: {
    population: Population[]; late_basis: LateBasis[];
    score_policy: ScorePolicy[]; period: Period[];
  };
  filters: {
    population: Population | null; late_basis: LateBasis | null;
    score_policy: ScorePolicy | null; period: Period | null;
  };
};
type BlockBResponse = {
  q6: { rows: Q6[] }; q7: { rows: Q7[] }; q8: { rows: Q8[] };
  q9: { states: Q9State[]; methods: Q9Method[] };
  q10: { rows: Q10[]; coverage: Q10Coverage[] };
  meta: BlockBMeta;
};
type LegacyBlockBResponse = Omit<BlockBResponse, "q6" | "q7" | "q8"> & {
  available: true; q6: Q6[]; q7: Q7[]; q8: Q8[];
};
```

Q6 `units_with_unknown_price` повторяется по истории товара: нельзя складывать
по датам. Q10 `within_score` допускает пересечение групп заказов, а причины
coverage могут пересекаться. В обоих population длительность/опоздание
измеряются только там, где их определяет исходная mart. Пустая группа Q10
сохраняет count 0 и NULL среднего/доли. Неизвестные цена, дата, штат, сумма
и тип платежа сохраняются отдельно; связи оценки и срока не заявлены причинными.

## Проверки

Все проверки выполнены на существующих инструментах, без установки зависимостей.
Guard `2026-10-28T14:08:39Z`: exit 78, free SSD 26.38 GiB, memory pressure 2,
swap 3.68 GiB. Heavy local/full fixture/build не запускались.

```sh
node --test app/api/tests/block-b.test.js
node --check app/api/block-b.js
node --check app/api/server.js
python3 app/api/tests/block-b.pg16.py
git diff --check
```

Node: **10/10 PASS**. Исполнен настоящий код `server.js`, cache, mount и pg
parser registration в VM с inert Express/pg adapters, без слушающего socket.
Проверены семь источников/параметры, allowlist и негативные входы, оба контракта,
сохранение NULL, отсутствие дублирующего route, существующий Q1–Q5 route,
400/500/200, missing каждой из семи views, timeout/connection/column error,
отсутствие кэширования ошибки и cache hit/recovery. Это не реальный Express HTTP.

PG16: небольшой собственный временный PostgreSQL **16.15**, Unix socket,
TCP отключён, `shared_buffers=16MB`, 10 синтетических заказов. Загружены точные
10/20/40/55 из input, без изменения исходников модели. Node reader исполнил
подготовленные SELECT через psql/JSON bridge: проверены реальные поля против
information_schema, NULL цены/даты/штата/суммы, два окна Q9, все 16 сочетаний
enum, 40 Q10 rows / 5 выбранных, 2 coverage rows, ошибка после удаления своей
view. Основной Q7 пуст при пороге 500; совместимый reader возвращает 8 групп
ниже порога для счётчика существующей страницы. Все созданные временные runtime
удалены после остановки собственных серверов PG.

Финальный фактический прогон `2026-10-28T14:17:22.907357+00:00`:

```json
{
  "status": "pass",
  "scope": "synthetic_stage55_psql_bridge",
  "postgres": "16.15",
  "orders": 10,
  "combinations": 16,
  "rows": {"q6": 16, "q7": 0, "legacy_q7": 8, "q8": 2, "q9_states": 1,
           "q9_methods": 6, "q10": 40, "q10_coverage": 2},
  "missing_view": "rejects",
  "own_server_stopped": true,
  "runtime_removed": true,
  "actual_express_pg_http": "not_run",
  "full_olist": "not_run"
}
```

SHA256 фактически проверенных файлов:

```text
app/api/block-b.js                   7babaad833f45057e5f0a213b82ea1069d875baaa706112854a3a48e82dbcd0a
app/api/server.js                    3ff38350f649610e58d9efd28cd19fd9d8da91f08c1566216c4d83242d3b8621
app/api/tests/block-b.pg16.mjs        0f16a81f25832f5bfcaf5ed2ca5f3ea48cad48a66e1054bdef99fea4e663ad9d
app/api/tests/block-b.pg16.py         6fa630ae50a5df156c62dbfdeacd2b08a3af64126adeb2c32dd608bf3847d4c4
model/55_answers_block_b.sql         34e0f6f5f03f2d013b82e1acb0dc9ec4db66366fc918d0a81136a01193e6b1b4
```

Первый запуск завершился assertion `30 !== null`: fixture разнесла известный
и неизвестный платежи в разные штаты. Исправлена только fixture (оба заказа
помещены в неизвестный штат), не production SQL/API; повтор прошёл. Отказ не
выдаётся за обнаруженный дефект бизнес-SQL.

**Unchecked:** installed Express+pg HTTP, настоящий браузер/UI, deployed service,
полный Olist DB lifecycle, CSV→raw equality и итоговые реальные Q6–Q10 числа.
Прежние CSV oracle и малый PG16 не являются полным DB PASS. UI `6452806`
пока имеет более узкие nullable types и сам выбирает оформление строк/графиков;
передача NULL по API не доказывает визуальную приёмку.

## Коммиты и интеграция

1. `1f5181ca54d78282b5ef4062af2ba0abab305640` — ownership и точная копия
   опубликованного `server.js` из `6452806` как API baseline. Это не повторная
   реализация страницы. На main `6452806` эту baseline-часть переносить не нужно.
2. `f2ed18d2083ac651fc0cb7aa500053d0e3b6b185` — общий reader, совместимый
   `/api/answers-b`, согласованный адаптер, 10 Node tests.
3. `ddddf48d0ca05e9b0be40369c635b2274ccdc084` — воспроизводимая малая PG16
   проверка, не full fixture.
4. Финальный doc commit содержит этот готовый handoff; опубликованный tip SHA
   указан в итоговом сообщении.

Для ревью изменения API относительно коллеги:

```sh
git diff 6452806eae21d13126da9de8ebaba01a2152eaea f2ed18d2083ac651fc0cb7aa500053d0e3b6b185 -- app/api
git diff aab62d7a59f196be051df12466fb21c0da4659b9 HEAD --name-only
```

Ветка основана на aab, а не на новом main. Не копировать всё её дерево поверх
main: функциональные коммиты предназначены для переноса владельцем интеграции
с сохранением изменений UI коллеги. Дифф коммитов меняет только OWNED paths.
Основной dependency — семь views stage 55 из aab. В main `6452806` файла 55 и
его подключения ещё нет; `make build` только этого main их не создаст.
Это требует интеграции модели её владельцем, а не пустого успеха API.

Предпубликационная сверка после fetch: main остаётся
`6452806eae21d13126da9de8ebaba01a2152eaea`, integration branch —
`aab62d7a59f196be051df12466fb21c0da4659b9`. Diff подключения от API baseline
применён **только к временной текстовой копии** target `server.js`: `git apply
--check` PASS, результат побайтово равен проверенному файлу proposal. Временный
каталог удалён. Merge, checkout целевого main и общий index не использовались.
`package.json`/lock не отличаются от target; stage 55 не изменился на опубликованной
integration branch. Список итоговых изменений — ровно шесть OWNED файлов.
Файлы `app/web/**` не входят ни в один коммит этой реализации.

Далее: интегрировать функциональные коммиты с опубликованными model/history
изменениями, проверить endpoint на согласованной полной БД и принять
существующую страницу на реальных NULL/coverage/ошибке. Здесь shared checkout,
model, UI, deploy и чужие процессы не менялись.
