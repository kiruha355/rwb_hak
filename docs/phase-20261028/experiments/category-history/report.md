# История категорий: инженерный эксперимент

> Снимок handoff: описания «локально», «не опубликован» и «публикация pending» ниже относятся к моменту подготовки отчёта. Эти report, script и results входят в опубликованное дерево `aab62d7a59f196be051df12466fb21c0da4659b9`; статус проверки и отсутствие human approval от публикации не меняются.

## Scope

- Owner: research sub-agent category-history, назначен в текущем запросе; координатор Sol.
- Repository/branch: kiruha355/rwb_hak, общий checkout main; HEAD 2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e.
- Base: published main bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4; SQL candidate 99bcbb366720f912ef6017a40aa5dbd6a671a8a4; integration b0bd0200a0a88b6bb7eb242cfc11d3239ff0fb68.
- Owned paths: docs/phase-20261028/experiments/category-history/** only.
- Status: ready_for_review (local); next: coordinator review/publication and separately authorized model implementation.
- UTC registration: 2026-10-28T13:30:41.378346+00:00.
- Scope registration here is the explicit user override; shared registry/index untouched. No model changes, commits, DB/runtime, installs, subagents or thread messages.
- Evidence boundary: CSV observations and Python simulation; no core execution or human approval claimed.

## Вывод и критерий

Рекомендация: **неизменяемый baseline + журнал category events + неизменяемые releases привязок item→category-version**. В `core` хранятся сохраняемые таблицы источника истории, исключённые из destructive rebuild; `dim_category_version` и факты — восстанавливаемые проекции. Первая версия Olist честно называется `snapshot_at_bootstrap`, её business valid time неизвестен. Новые seller overrides существуют рядом с product baseline. Опубликованные отчёты используют сохранённые привязки; исправленная аналитика выпускается отдельным `restatement`.

Критерий выбора, в порядке важности:

1. Одинаковый `report_release_id` всегда даёт ту же совокупность позиций, категории, суммы и подписи после смены категории, backdating и пересборки.
2. Из сохранённых входов можно восстановить всё на пустой БД. Ни одна нужная версия не существует только в таблице, которую удаляет `00_schemas.sql`.
3. У каждой привязки видны источник, scope, причина выбора и граница знания; неизвестное бизнес-время не маскируется датой.
4. Действие одного продавца не меняет другого без явной authority на product scope.
5. Реализация встраивается в существующую транзакционную сборку и объяснима на нескольких строках. Производительность здесь не измерялась и победу не определяет.

Это инженерная рекомендация, **не human approval**. Оба реализуемых способа сохранения истории ниже проходят критерии 1–2 при наличии release manifest. Журнал предпочтителен по 3–4: он явно фиксирует операцию, её автора и исправления. Неизменяемые снимки остаются способом загрузки исходного baseline, checkpoint и обмена, поэтому выбирать один формат навсегда не нужно.

## Проверенные входы и пределы baseline

Требование вброса прочитано на [точном commit организаторов](https://github.com/daniilivanovp-droid/hackathon-students/blob/558f0f6a38110acc9fcf4386a7e53ece973aedf5/docs/tasks.md#L79-L84): сохранять прежние отчёты при изменении категории продавцом. Локальная точная копия — [tasks.source.md](tasks.source.md), SHA-256 `c24f3190729a672c09fcb97854a678fa02712456350038ff2bd738095652d1c5`. Исторические категории Olist этот текст не предоставляет.

На старте `git fetch --all --prune` успешно завершился; проверенный `origin/main` — `bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4`. Dirty checkout оставлен на `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`. Ни pull, ни merge, ни reset не выполнялись. Проверены локальные AGENTS, workstreams, decision-log, ideas, research/README и postmortem. Индекс исследований существует локально и в опубликованном main; локальный текст может отставать от remote. Из postmortem применены: реальные строки, конкретная операция, проверка target Git blobs и раздельные уровни доказательств.

[results.json](results.json) содержит полные SHA-256 всех 8 CSV, заголовки и количество записей. Они совпали с опубликованным baseline `bbbfab8:research/internet-2026-10-28/orchestrator/evidence/sol-independent-check.json`. Всего **550 759 CSV records**; данные читались потоково, в памяти только компактные ключевые карты/счётчики, без pandas. Хеши CSV проверены повторно после эксперимента. Это **CSV observation**, не проверка фактического содержимого `raw` или результатов `core`.

| Наблюдение CSV | Результат |
|---|---:|
| Товары | 32 951 |
| Товары без категории | 610 |
| Позиции | 112 650 |
| Различные `(product_id, seller_id)` | 34 448 |
| Товары с несколькими продавцами | 1 225 |
| Позиции этих товаров | 14 416 |
| Максимум продавцов одного товара | 8 |
| Категории в delivered revenue, включая unknown | 74 |
| Delivered `sum(price)`, без доставки | 13 221 498.11 |

В `products` есть ровно одна категория на product, нет даты назначения и seller_id. В items есть seller_id, но нет категории на момент продажи. Из разных продавцов и цен нельзя вывести изменения категорий. Из отсутствия seller category в CSV нельзя вывести запрет такого свойства в будущей системе.

Реальный пример: product `99a4788cb24856965c36a24e339b6058`, baseline `cama_mesa_banho`:

| seller_id | Позиции, все статусы | Delivered revenue |
|---|---:|---:|
| `4a3ca9315b744ce9f8e9374361493884` | 482 | 41 542.50 |
| `53d00c40e32aeb924a84ce72b1af869d` | 6 | 507.16 |

Позиция `(0006ec9db01a64e59a68b2c340bf65a7, 1)` принадлежит первому продавцу, цена 74.00, purchase `2018-07-24 17:04:17`. Позиция `(0504c112cd5ef9650a65748c4dc380cb, 1)` — второму, цена 86.00, purchase `2018-04-17 09:10:35`. **Это не A→B история.** Это доказательство blast radius: глобальное обновление категории product затронуло бы обе группы, хотя инициатором мог быть лишь второй продавец.

## Где теряется история в текущем SQL

SHA-256 файлов `model/00_schemas.sql`, `10_dims.sql`, `20_facts.sql`, `40_mart.sql` совпали между local working tree, published main `bbbfab8`, candidate `99bcbb366720f912ef6017a40aa5dbd6a671a8a4` и integration `b0bd0200a0a88b6bb7eb242cfc11d3239ff0fb68`. Хеши каждого blob записаны в results. `model/build.sql` в integration отличается: добавлен этап 55; локальный build пока равен main/candidate.

| Код | Текущее поведение | Необходимая правка при реализации |
|---|---|---|
| `model/00_schemas.sql:31` | Явно удаляет facts, dim_product, dim_category с RESTRICT, внутри транзакции | Сохраняемые category source/release таблицы не включать в DROP. Новую производную version table включить в owned drop graph |
| `model/10_dims.sql:249`, `:281` | Категории из raw и один category_key на product | Сохранить baseline product, загрузить категории всех используемых версий и построить отдельную version dimension |
| `model/20_facts.sql:133` | PK `(order_id, order_item_id)`, product/seller, без category version | Добавить NOT NULL category_version_id, назначать из pinned release binding |
| `model/40_mart.sql:252–259` | Категория item через текущее `p.category_key` | Для historical report соединять item→version→category; current category вынести в отдельную view |
| `model/build.sql`, wrapper | Одна транзакция, repeatable read, raw reload barrier, advisory lock | До DROP валидировать source/release manifests; pin release и источник, включить проверки bindings до COMMIT |

Смена current `dim_product.category_key` меняет категории всех старых позиций. Добавление SCD2 только в `10_dims.sql` не исправит это, если предыдущие версии удаляются в `00` и неоткуда восстановить их при rebuild. Поиск `category_history/category_event/category_version/valid_from/valid_to` в опубликованных `model/` и `scripts/` не обнаружил существующего источника версий.

Интеграционная оговорка: `b0bd020` добавляет views Q6–Q10 через 55, но его `00` совпадает с main и не перечисляет эти views. До приёмки повторной сборки нужно проверить полный dependent-view graph и добавить принадлежащие модели views в inventory; здесь это статическое замечание, не воспроизведённая ошибка PG и не выполненная правка.

## Сохраняемый источник и честная начальная точка

**Существующий источник baseline** — точные bytes `data/olist_products_dataset.csv` (SHA-256 `3e6569628a17fbc75fd206ee357b59e20364b9afa90f5b6cd5b4d624c58aa9cc`), translation CSV (`a81f0d1f27b27e7293f761bc79e3ce8f348ee39c4b3ed3e49bde38f478586278`) и остальные 6 файлов для полного report dataset. Сохранение hashes без самих bytes недостаточно: при реализации нужен защищённый immutable artifact store/архив вне Git и вне disposable database. URL на pinned Olist ref — дополнительный адрес получения, а не резервная копия. Архив в этой задаче не создавался.

**Источника реальных изменений пока нет.** Его надо начать вести в момент подключения функции изменения категории: authenticated command/API → транзакционная запись event/outbox и catalog update → acknowledgment. Если каталог находится в другой БД, принимать durable outbox/CDC с source_event_id, source_revision и дедупликацией; нельзя сначала менять каталог, а потом best-effort писать историю. CSV import должен приносить неизменяемый package с provenance; позднее наблюдение current-state само по себе не даёт точного времени изменения.

Bootstrap выполняется один раз для принятого manifest:

1. Проверить CSV hashes/headers/keys и raw↔CSV equality в разрешённом integration run; зафиксировать `dataset_id` как hash manifest.
2. Сохранить baseline product→category с `business_valid_from=NULL`. `captured_at/recorded_at` — реальный момент фиксации, хранимый в manifest, **не `now()` при каждом rebuild**. Не подставлять начало Olist, первую продажу, mtime файла или дату Git commit как начало действия категории.
3. Назначить всем 112 650 исходным item keys baseline version с `attribution_basis=snapshot_at_bootstrap`. Это первоначальная классификация данного снимка для отчётов; утверждение «так было на дату заказа» из неё не следует. Базовые категории считаются на всех items, статус delivered применяется уже метрикой.
4. Сохранить release R0: population, item payload hashes, bindings, категории/labels, остальные raw artifacts, code/policy refs и canonical output digest. Старые периоды R0 больше не переклассифицируются. Опубликованный маршрут `(report_kind, closed_period) → release_id` закрепляется: обычный экран прошлого периода открывает этот original release, а не автоматически latest. Без такого маршрута неизменяемые архивы не предотвращают незаметную смену цифр на экране.
5. Публиковать будущие изменения только из новых packages. Каждая обычная extension наследует прежние bindings и добавляет только открытые периоды; correction и late-arriving item закрытого периода создают отдельный proposed restatement. Они не переназначают original route без решения о публикации пересмотра. Hash-identical bootstrap retry — no-op; другой baseline manifest не перезаписывает R0, а создаёт отдельный dataset/release.

События, появившиеся после bootstrap, не «восстанавливают» историю 2016–2018. Учебный пример ниже полностью синтетический. Для поздно пришедшего исторического item без сохранённой binding нет доказательства старой категории: допустим новый release с явно помеченным snapshot fallback/unknown_history, но нельзя молча назвать это actual as-of.

## Product baseline и seller overrides

Хранить одновременно:

- `product_id → product category baseline/events`: глобальный уровень каталога.
- `(product_id, seller_id) → override events`: уровень предложения конкретного продавца.
- `order_id, order_item_id → выбранная category_version_id`: стабильная связь факта с классификацией.

При разрешении категории: активный seller override → активный product event → baseline snapshot → явно маркированное unknown. `set category=unknown` — реальное назначение неизвестной категории, не команда удаления override. `unset_override` — отдельное действие, которое возвращает fallback на product. Изменение product baseline не обходит действующий seller override. Возврат A→B→A создаёт новую version identity A2; equality имени категории не схлопывает историю.

Seller identity Olist достаточно для демонстрации `(product,seller)`; она не доказывает существование единственного offer/SKU у этого продавца. Если в продуктовой системе один seller продаёт несколько независимых listing одного product с разными категориями, понадобится `offer_id`, а mapping к Olist остаётся агрегированным. Это условие расширения модели, не причина задержать текущую реализацию.

Право редактирования отдельно от scope данных: обычный продавец получает seller scope; product scope требует полномочий catalog owner. Из технической схемы право продавца менять глобальный каталог не выводится. Можно одновременно показывать product taxonomy и seller merchandising category, именуя их явно; default historical metric берёт сохранённую effective binding. Оба разреза сохраняют одну строку на item и должны отдельно сходиться с общей выручкой. Нельзя складывать их как независимые продажи.

## Наблюдение, бизнес-время и исправления

| Поле/ось | Значение | Чего не доказывает |
|---|---|---|
| `source_observed_at` | Когда источник заметил состояние | Когда оно началось в бизнесе |
| `recorded_at` | Когда доверенный ingest принял event | Время покупки/изменения категории |
| `business_valid_from` | С какого бизнес-времени источник утверждает изменение | Что это уже было известно в старом отчёте |
| `policy_apply_from` | Объявленная граница применения observed-only события к будущим заказам | Историческую effective date |
| release package set/cutoff | Какие версии были доступны конкретному выпуску | Самую новую истину на сегодня |

В model покупка — naive timestamp. Ingest receipt — UTC timestamptz. Их нельзя непосредственно сравнивать. Для новых events фиксируется `business_clock_contract`/time zone, либо событие и item приходят с сопоставимым источниковым ordering token. При неизвестной зоне Olist мы не выбираем UTC или Brazil zone задним числом. Для демонстрации используются символические времена; будущая observed-since policy обязана явно определить перевод receipt в бизнес-часы или применять категорию по source capture ordering. При отсутствии такого контракта observation сохраняется, но не участвует в automatic as-of.

Нормализованные интервалы `[from,to)` строятся для одного scope и одного knowledge snapshot. В момент from действует новая версия; до from — предыдущая. Baseline с неизвестным началом **не превращается в `[-infinity,first_event)` как доказанная история**: это отдельный fallback с basis. Version identity — content-derived ID события/базовой строки; меняющийся при появлении следующего события `valid_to` не должен менять FK старого item.

Коррекция не UPDATE старой строки. Новый event с `supersedes_event_id` хранит исправление, reason, authority и receipt. При построении knowledge snapshot сначала ограничить events пакетами release, затем исключить superseded events, затем построить интервалы. Иначе поздняя коррекция «протечёт» в старый отчёт. Коррекция может изменить valid_from или category; исходная версия доступна для старых releases. Она относится к той же product/seller scope; перенос scope оформляется отдельными явными операциями. Ветвящиеся corrections и разные события с одинаковой effective boundary без source precedence блокируют публикацию, а не разрешаются случайным UUID/порядком загрузки.

Backdating меняет `restated` отчёт, не исходный. Если требуется держать **все** ранее закрытые периоды неизменными при любой поздней информации, важна не только категория: новые/изменённые строки, цены, статусы delivered и labels тоже фиксируются release manifest. Один SCD2 не способен заморозить весь отчёт.

## Два реализуемых подхода

| Критерий | A. Immutable catalog snapshots + release bindings | B. Append-only event ledger + release bindings |
|---|---|---|
| Сохраняемый источник | Полные product defaults + seller overrides каждого снимка, metadata/manifest, item bindings | Baseline snapshot + ordered immutable event packages + bindings/checkpoints |
| Встраивание в 00/10/20/40 | 00 сохраняет source tables; 10 читает pinned snapshot versions; 20 берет binding; 40 joins version | Те же границы; 10 replay events до pinned package set, materializes versions; 20/40 те же |
| A→B | Новый snapshot S1, S0 не удаляется | Новое событие E1; предыдущая запись остаётся |
| Backdated correction | Новый snapshot/release, ссылка на superseded snapshot; нужно добавить declared valid time/revision metadata | Новый event supersedes старый; знание и business boundary отдельны |
| Источник только polling current catalog | Воспроизводимы наблюдения; переход A→B→A между опросами потеряется | Без event/outbox тоже не восстанавливает ненаблюдаемые переходы |
| Автор/authority изменения | Нужны delta metadata/audit log сверх снимка | Естественные обязательные поля события |
| Rebuild cold DB | Restore exact snapshots + bindings; build projections | Restore baseline + full event chain + bindings; replay/check |
| Объём | O(products × snapshots), плюс overrides и bindings | O(products + changes), плюс bindings/checkpoints |
| Риск | Подменить observation бизнес-историей; полный snapshot пропустит быстрые смены | Сложнее correction/ordering validation; потеря event package ломает replay |
| Пригодность | Хороший bootstrap/контрольный снимок; полноценный вариант при source snapshot на каждое изменение | Рекомендуемый основной путь при контроле change API/outbox |

Оценки объёма — логические, не benchmark. На этих данных полное разворачивание baseline на все наблюдённые product-seller pairs даёт 34 448 строк вместо 32 951, но сам baseline источник всё равно product-level. Дублировать его как будто мы наблюдали seller assignments не требуется. Binding на 112 650 items имеет явную цену хранения, зато позволяет обеспечить проверяемую неизменность. Сначала простой полный release binding; delta manifests/checkpoints можно добавить при измеренном росте, сохранив deterministic materialization.

**Отброшено по критерию:** current product join; SCD2 в пересоздаваемой таблице без источника версий; назначение fake historical valid_from; полная замена product identity на seller-product с приписыванием baseline продавцам; применение поздней correction к старому published ID; выбор latest без явного report version. **Оставить оба:** product baseline и seller overrides, original и restated отчёты, event ledger и immutable snapshot checkpoints.

## Минимальный алгоритм и DDL-план

[ddl-plan.sql](ddl-plan.sql) — конкретный, но **не исполненный** PostgreSQL DDL-план. Persistent objects: `category_source_package`, `category_baseline`, `category_event`, `category_report_release`, `category_report_binding`. Disposable projection: `dim_category_version`; `fact_order_item.category_version_id`; historical mart join. Persistent tables не имеют FK на disposable facts/dimensions, иначе RESTRICT будет блокировать rebuild. Derived tables могут ссылаться на persistent источник.

```text
ingest(change):
  authenticate scope; canonicalize payload; derive stable event/content ID
  under product-level lock, check expected source revision and correction chain
  exact source identity + exact payload -> return previous receipt
  same identity + different payload / conflicting authority -> reject
  append event and durable publication package; commit before acknowledgement

publish_release(parent, input_manifest, event_package_set, policy):
  verify bytes, source IDs, complete packages, taxonomy and clock contracts
  inherit parent's bindings unchanged for extension; freeze closed-period membership
  for each new item / explicitly authorized restatement item:
    limit events to package set; resolve corrections visible in that set
    select latest applicable seller event (unset means fallback)
    else select product event; else explicit baseline/unknown-history binding
    reject ambiguity; store selected version, item payload hash and basis
  validate population, keys, totals and frozen-parent bindings
  persist immutable manifest + all bindings in one transaction

rebuild(release_id):
  restore/verify retained source packages if clean database
  load exact raw generation through separate loader; verify raw↔artifact equality
  begin existing locked repeatable-read build transaction
  00: drop only owned disposable graph
  10: rebuild baseline dims, retained category domain and stable version IDs
  20: join exact item binding; reject absent/extra/changed item before publication
  40: historical category = item.version.category; separate current view
  90: checks, canonical report digest, commit
```

Здесь `event_package_set` надёжнее одного timestamp cutoff: событие с прошлым source timestamp, принятое позднее, не должно появиться в уже опубликованном наборе. `recorded_at` назначается ingest, не доверяется клиенту; package list фиксирует точное множество. Content IDs вычисляются по специфицированному canonical serialization: UTF-8, stable key ordering, timestamps по контракту, числовые строки без float, с разделением namespace/scope. Hash проверяет целостность, не полномочия автора.

Для release в основной rebuild выбирается ровно один dataset/report scope. При полном восстановлении старого release с другим raw generation **нельзя менять живой raw в рамках model build**: отдельная пустая БД из архивных bytes и штатный loader. На live raw, не совпавшем с release manifest, сборка должна остановиться до DROP. Для одновременного просмотра нескольких releases возможны отдельные materialized exports/таблицы keyed by release_id; это следующий слой, не смешение двух grains в текущем fact.

## Учебный эксперимент A→B

[script.py](script.py) выполняет baseline audit и **синтетическую stdlib simulation**, не SQL и не реконструкцию Olist. Символические времена `5, 10, 12, 20` не являются датами исходных данных.

| Шаг | Категории/операция | Полученный результат |
|---|---|---|
| R0 | Product P baseline A; старые позиции S1=100, S2=200 | A=300 |
| E1, t=10 | Seller S1 назначает B; S2 наследует A | R0 остаётся A=300 |
| R1 | Добавлены позиции t=12: S1=30, S2=40; старые bindings сохранены | A=340, B=30 |
| Ошибочный current-product join | Product P глобально заменён на B | B=370; старые периоды и второй seller переклассифицированы |
| E2, известно t=20 | Исправление E1: B действует с t=4 | Original R1: A=340, B=30; restated R1: A=240, B=130 |
| Product C, затем unset S1 | Глобальная категория C; override S1 сначала B, затем снят | Пока override активен S1=B/S2=C; после unset S1=C |
| Observed-only D | valid time отсутствует, явная observed-since policy | До наблюдения C; после D с basis=observed_since_policy |

19 assertions проходят: A→B, сохранность старого отчёта, seller isolation, current-join counterexample, retry, конфликт ID, backdating, replay старого cutoff, полный cold replay R1, граница `[from,to)`, сосуществование scopes, unset, observation boundary, explicit unknown, возврат к baseline с новым version ID, альтернативный snapshot restore, late item, simulated rollback и отказ при неоднозначной границе.

Snapshot alternative проверен на восстановлении immutable bindings R0/R1; полноценный snapshot ingest/CDC не реализован. Simulated rollback проверяет «не публиковать невалидный candidate» в Python, **не ACID PostgreSQL**. Полное исчезновение core моделируется повторным вычислением bindings из baseline+events+pinned cutoff; DDL rebuild фактически не выполнялся. Поллинг A→B→A между снимками даёт A,A — конкретный контрпример невозможности восстановить ненаблюдаемое B.

## Инварианты, rollback и защита raw

1. Exactly one binding на `(release_id, order_id, order_item_id)`; item product/seller/payload hash совпадает с выбранным raw generation; число bindings равно population. Нет INNER JOIN, скрывающего отсутствующие соответствия.
2. Каждый version ID стабилен между rebuild и существует в version dimension; category domain содержит все referenced исторические категории, включая unknown и отсутствующие в текущем каталоге. Переименование/translation labels фиксируются release taxonomy, иначе старый отчёт поменяется визуально даже при прежних суммах.
3. Отдельно проверять no overlapping intervals **внутри одного scope/knowledge snapshot/clock basis**; overlap product и seller разрешён и решается precedence. Baseline NULL boundary проверяется как специальный fallback, не интервал. Диапазоны `[from,to)` поддерживаются [PostgreSQL ranges](https://www.postgresql.org/docs/16/rangetypes.html); можно проверять через window lag, без установки расширения.
4. Original release bindings и canonical report digest неизменны после event append/correction/rebuild. Extension не удаляет parent items и не меняет parent payload. Изменённые цена/статус/популяция требуют нового dataset/release, иначе нельзя обещать прежние итоги.
5. Для каждого category mode сумма item revenue по категориям равна общей выручке на одной population. Число строк после version join не растёт. Unknown coverage показывается явно. Pinned regression 13 221 498.11 относится только к baseline, не к любому будущему raw.
6. Import повторяется идемпотентно, конфликт одного ID блокируется; correction target существует, scope совпадает, chain ацикличен; unseen missing package либо digest mismatch блокирует rebuild. Ни hash, ни timestamps не разрешают бизнес-конфликт сами по себе.
7. Сборка старого release не читает live latest events. Параллельный ingest не меняет закреплённый package list. Repeatable read помогает согласованному чтению, но сам по себе не сериализует writers и не заменяет locks/retry протокол; это соответствует [PG16 isolation](https://www.postgresql.org/docs/16/transaction-iso.html).

Rollback сборки: существующая транзакция возвращает прежний core при SQL error; candidate release не становится current до проверок. Source history не удаляется при неуспешном build. Если ingest уже committed, событие остаётся accepted source evidence, но не published report. При сомнительном исходе COMMIT сначала readback release ID/digest, затем retry, без «повторить всё» вслепую. Rollback бизнес-изменения — compensating event/новый release, не DELETE истории. Исторический original report доступен по прежнему ID.

Защита `raw`: модельному build role только SELECT/необходимые REFERENCES, без INSERT/UPDATE/DELETE/TRUNCATE/CREATE/ownership raw; raw_owner и category_history_owner отделены от rebuild role. History owner — не build owner; persistent objects не входят в drop inventory. В PostgreSQL владелец сохраняет право менять/удалять объект, поэтому одного REVOKE недостаточно, если build запускается owner/superuser; см. [PG16 privileges](https://www.postgresql.org/docs/16/ddl-priv.html). Сейчас запуск с `hack` не считается доказанной read-only границей: роли не проверялись и не менялись.

Новые функции ingest/release требуют узкого EXECUTE, фиксированного search_path, валидации authority и явной сериализации. Рекомендуемый deployment использует durable artifacts с отдельным backup/restore и access policy. Эти механизмы здесь спроектированы, но не развернуты. Все CSV использовались read-only, их bytes до/после совпали.

## Что ещё действительно требует человека

**Для технического продолжения не остаётся равнозначной развилки, которая блокирует работу.** Можно поддержать оба scope и оба report modes, сделать original неизменным по умолчанию, restatement отдельным, неизвестное время честно маркировать. Не требуется заранее заставлять человека выбрать product *или* seller-product.

Остаются внешние полномочия и семантика источника, которые эксперимент не устанавливает:

- Кто вправе публиковать глобальное product изменение и кто санкционирует restatement уже выданного отчёта. Можно реализовать оба scope/mode заранее; включение полномочий требует владельца продукта/данных.
- Если вход содержит только product_id без seller_id и заявленную «смену продавцом», нельзя угадывать seller. Сохранить unresolved evidence, потребовать scope от источника. Это недостающий факт, а не равнозначный архитектурный выбор для общего опроса пользователя.
- Какое время источник считает моментом смены и в каких часах оно задано. Без source contract сохраняется observation, baseline release защищён; доказанный business as-of для будущих заказов невозможен. Команда выбирает observed-since policy лишь как явную договорённость, а не как найденную историю.
- Как назвать официальный пересмотренный выпуск и когда его объявлять новым актуальным отчётом. Поддержка original + restated снимает техническую дилемму; решение о публикации принадлежит ответственному человеку.

Если требуется «восстановить действительные категории всех заказов Olist в 2016–2018», это **неразрешимо на имеющихся входах**, независимо от голосования или выбранного SCD. Нужен внешний category-change ledger/исторические snapshots с provenance. Человек может определить допустимую baseline семантику, но не сделать отсутствующую историю наблюдаемой.

## Handoff

- Status: `ready_for_review` локально; не `done`, remote publication SHA не создан. Рекомендация не выдана за approval.
- Artifacts: [script.py](script.py), [results.json](results.json), [ddl-plan.sql](ddl-plan.sql), [tasks.source.md](tasks.source.md), [flow.html](flow.html), этот report.
- Изменения только в owned directory. `model/`, registry/index, raw/CSV и общая Git index не менялись. Чужие треды/субагенты не вызывались; installs/DB/runtime не запускались.
- Воспроизведение: `python3 docs/phase-20261028/experiments/category-history/script.py`. Нужны stdlib Python3, локальные 8 CSV и Git objects трёх указанных refs; network не нужен. Script fail-fast при baseline drift и requirements hash mismatch; deterministic `results.json` содержит hash самого script. Это запускает небольшой streaming audit, не heavy fixture.
- Проверено: CSV hashes/header/count baseline, category/identity counters, static code blob equality, 19 synthetic assertions, неизменность CSV, identical results SHA-256 после повторного запуска. Не проверено: SQL syntax/runtime DDL, permissions, concurrent ingest, реальный rollback, full CSV→raw→core→report; scope симуляции обозначен выше.
- Следующий implementation task для владельца модели: внедрить persistent source migration и pinned release bootstrap, version FK и mart join; затем на разрешённом маленьком PG16 стенде прогнать A→B/correction/duplicate/unset/late item/failed rebuild/clean restore с raw hash readback. Полный pipeline — отдельный проход по guard, не следствие Python PASS.
- Обязательные acceptance evidence: hashes источника и code, original/restated results, raw до/после, clean restore report digest, проверенный target Git tree после публикации. Артефакты ожидают публикации координатором.

UTC handoff update: 2026-10-28T13:44:31.551477+00:00.

Повторный offline запуск дал byte-identical results.json: SHA-256 `74ab4b165ad7c9fc8cff9b4507a123a870157bb26b8b96ed8bcf451c6432eef0`. Visual QA flow.html: html_preview 728px, contentHeight 567, consoleMessages пуст. Closed-period route описан как дополнительный publication contract; в simulation проверена неизменность releases, UI routing не реализован.
