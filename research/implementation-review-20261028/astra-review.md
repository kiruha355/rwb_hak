# Независимый review реализации · W-13

**Вердикт: нужны исправления перед full-model acceptance.** Найден один P1 в обязательном пути CSV→raw и четыре узких P2. P0 не найден. Разделение grains и основная семантика core/mart выглядят корректно; это поддержано не только статикой, но и просмотренным evidence W14 о 16 малых PostgreSQL-сценариях. Полная сборка Olist, опубликованные ответы из core, shell-wrapper clean/rebuild/late rollback и CSV↔raw binding остаются **не подтверждены**.

Reviewer: GPT-6 Astra, HIGH, без Fast; без делегатов. Repository `kiruha355/rwb_hak`, shared dirty checkout `main`; локальный HEAD `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`, после успешного fetch `origin/main` — `1939068295d7203a15cbb0a1ab5d407caca90f58`. Ни index, ни локальные ветки, ни чужие файлы reviewer не менял; ничего не опубликовано. Единственные записи reviewer: этот файл и [astra-evidence.json](astra-evidence.json).

Вход — [review-input.json](review-input.json), 29 файлов. Все 29 SHA совпали при начале и повторной проверке в `2026-10-28T10:04:27.789781+00:00`; drift не обнаружен. SHA самого manifest, полный список начальных/конечных SHA и дополнительные прочитанные входы — в evidence и приложении ниже. Вердикт относится к этим байтам, а не к будущим исправлениям.

Основное направление принято пользователем. Детализированный пакет человек рассматривает; 17 отдельных approvals здесь не приписываются. W12 и остальные независимые потоки могут продолжать работу.

## Findings

### R1 · P1 · CSV→raw verification всегда останавливается на CREATE TEMP в READ ONLY

**Место:** [scripts/verify-model.py:80](../../scripts/verify-model.py), `raw_inputs()` на строках 171–187, в особенности 182; вызывающий [tests/model/validate-lifecycle.sh:26](../../tests/model/validate-lifecycle.sh). Документация повторяет неверную предпосылку в `docs/model-validation.md:30`.

**Trigger:** подготовлены корректные pinned CSV, PostgreSQL 16 connection и `RWB_RAW_RELOAD_PAUSED=1`; запускается `--raw-inputs` или lifecycle. `connect(..., fixtures=False)` устанавливает `readonly=True`. Следующий этап пытается исполнить `CREATE TEMP TABLE ... ON COMMIT DROP` в этой read-only транзакции. PostgreSQL разрешает DML в уже существующей temp table, но запрещает **все CREATE**, в том числе временных таблиц. Это следует непосредственно из [документации PostgreSQL 16 SET TRANSACTION](https://www.postgresql.org/docs/16/sql-set-transaction.html).

**Impact:** ожидаемое доказательство равенства CSV↔raw не может быть получено этим кодом; lifecycle обрывается до clean build. Это ошибка verification path, а не доказательство неправильных чисел в построенном core. Наличие CSV, совпавший manifest и 16 успешных fixture cases не закрывают её: fixtures используют `fixtures=True`, то есть другой режим соединения.

Минимальный SQL repro для отдельного разрешённого стенда:

```sql
BEGIN READ ONLY;
CREATE TEMP TABLE astra_raw_probe (v text);
-- Ожидаемая ошибка PostgreSQL: cannot execute CREATE TABLE in a read-only transaction.
ROLLBACK;
```

Здесь repro **не запускался в PostgreSQL**: вывод подтверждён статическим control flow и официальной семантикой PG16, а не выдуманным runtime-log.

**Точечная рекомендация:** создать temp tables в подготовительной транзакции этого же соединения с `ON COMMIT PRESERVE ROWS`, затем начать `REPEATABLE READ READ ONLY` для COPY в эти уже созданные temp tables и EXCEPT ALL; по завершении закрыть session. Альтернатива — read/write transaction под ролью с SELECT на raw и TEMP на БД, без прав записи в raw. Не подменять binding хешем JSON. Добавить малый интеграционный тест именно `raw_inputs()`, включая quoted empty против NULL и ошибку при изменении raw.

### R2 · P2 · Самопроверки не проверяют has_translation_row и реконструируют перевод через raw

**Место:** [model/90_checks.sql:78](../../model/90_checks.sql), строки 78–94; контракт `model/CONTRACT.md:66`; ограничение [model/10_dims.sql:240](../../model/10_dims.sql).

**Trigger:** корректная translation row `('null-english', NULL)` была загружена; после build `has_translation_row` у соответствующей category случайно стал false. Возможен и обратный дефект: true у известной PT-категории, которая отсутствует в переводах и имеет `name_en=NULL`.

**Before/after impact:** core больше не позволяет восстановить membership исходного справочника по заявленному контракту. CHECK допускает оба состояния при NULL English. Однако translation mapping выбирает target через `name_pt IN (SELECT ... FROM raw.product_category_translation)`, а category mapping вовсе не включает `has_translation_row`. Поэтому проверка использует источник для восстановления утраченного различия и не видит его потери.

**Repro/evidence:** в маленькой in-memory DuckDB probe использованы настоящий `dim_category` DDL и точные source/target SQL двух mappings из `90_checks.sql`. После смены true→false CHECK принят; оба направления EXCEPT ALL дали 0 различий для `translations` и `categories`. В `90_checks.sql` нет ни одного упоминания `has_translation_row`. Результат сохранён в `astra-evidence.json.translation_membership_probe`. Это исполнение конкретных SQL-проекций в DuckDB плюс статическая проверка оставшихся правил, **не** объявление PG-run всей функции.

Контрпример для будущего PG-теста после fixture с NULL English:

```sql
UPDATE core.dim_category
SET has_translation_row = false
WHERE category_key = 'pt:null-english';
SELECT core.run_checks(); -- должен обнаружить потерю membership
```

**Точечная рекомендация:** в target translation mapping использовать `WHERE has_translation_row`, включить флаг в полный category mapping с независимым expected membership и добавить обе мутации в негативные cases. Сама текущая загрузка в `10_dims.sql:256–261` выставляет флаг правильно; находка относится к полноте проверки, а не к доказанной порче текущего Olist.

### R3 · P2 · Q2 скрывает неполную выручку за пределами LIMIT 10

**Место:** [model/50_answers.sql:58](../../model/50_answers.sql), строки 58–71, в особенности `ORDER BY item_revenue DESC NULLS LAST LIMIT 10`.

**Trigger:** десять продавцов имеют полную выручку 100…109, одиннадцатый — позиции 1000 и NULL. Полный revenue одиннадцатого правильно становится NULL, но затем seller отбрасывается из топа. Все возвращённые строки показывают `revenue_price_missing_count=0`; из самого результата невозможно узнать, что среди кандидатов были неполные суммы.

**Impact:** unknown не превращается в ноль непосредственно, но результат выглядит окончательным «топ-10 всех продавцов», хотя сравнение не определено для части population. Известный subtotal 1000 здесь не заменяет неизвестный total: core допускает и отрицательные исходные amounts, поэтому из subtotal нельзя без дополнительных предпосылок выводить окончательное место.

**Repro/evidence:** выполнен actual `model/40_mart.sql` + `50_answers.sql` в существующем DuckDB с 11 tiny synthetic sellers; результат — продавцы `rank-s09`…`rank-s00`, суммы 109…100, missing counts=0. `rank-s10` с known sum 1000 и одной NULL price отсутствует. Полный результат — `astra-evidence.json.q02_unknown_ranking_probe`. Это проверка mart semantics, не PostgreSQL/Olist acceptance.

**Точечная рекомендация:** выделить all-seller aggregate и считать число неполных revenue candidates **до LIMIT**; возвращать его/статус полноты рейтинга вместе с Q2 и сохранять доступный список неполных продавцов. При неполноте явно обозначать рейтинг как «среди продавцов с полной выручкой», а не присваивать неизвестной сумме место. Добавить случай с 11+ продавцами: нынешние 93 checks эту потерю видимости не ловят.

**Контраргумент:** на закреплённом Olist нет показанного здесь NULL-price trigger; текущий baseline Q2 этим замечанием не опровергается. Найдена воспроизводимая ошибка обработки допустимого нового входа, значимая для вброса и заявленной политики unknown.

### R4 · P2 · Документированная lifecycle-команда не устанавливает обязательный verified-manifest token

**Место:** [tests/model/validate-lifecycle.sh:52](../../tests/model/validate-lifecycle.sh), строки 52–54; [scripts/build-model.sh:155](../../scripts/build-model.sh), control branch; `docs/model-validation.md:142`.

**Trigger:** оператор выполняет указанную команду `RWB_RAW_RELOAD_PAUSED=1 bash tests/model/validate-lifecycle.sh` в чистом окружении с подключением к dedicated DB, но без заранее экспортированного `RWB_VERIFIED_INPUT_MANIFEST_SHA256`. Даже после исправления R1 и успешных binding/build/rebuild/rollback/check скрипт приходит к `control`, который гарантированно возвращает exit 2 из-за отсутствующего значения.

**Impact:** подготовленный «полный протокол» не завершается как описано. Сборки к этому моменту уже закоммичены, evidence частичный; это не атомарный провал всего lifecycle. Сам `make build` этому замечанию не подвержен.

**Repro:** проследить неизменённые строки 24–54: assignment этой переменной отсутствует. Вызвать control без переменной после настройки остальных prerequisites — wrapper отклонит его до SQL. Runtime всего lifecycle reviewer не запускал.

**Точечная рекомендация:** после успешного CSV↔raw и core-check установить token из проверенного baseline manifest, предварительно сверив его eight-file binding с W11 pin, и лишь затем вызвать control. Если оставлять token ответственностью оператора — явно добавить prerequisite и раннюю проверку в lifecycle до двух committed builds. Не подставлять token заранее как замену реальной проверке. `docs/build-runbook.md:73–83` уже правильно объясняет различие между SHA audit manifest и SHA произвольного JSON, но самостоятельный lifecycle-пример этого не выполняет.

### R5 · P2 · Whitespace-only обязательные text keys проходят btrim-проверку

**Место:** [model/05_typecheck.sql:55](../../model/05_typecheck.sql), строки 55–57; аналогичные guards/CHECK в `10_dims.sql:13–19,175–176`, `20_facts.sql:32,81`; `90_checks.sql:182–183` проверяет только NULL/пустую строку.

**Trigger:** в маленьком fixture один unused customer context получает `customer_unique_id=E'\t'` (либо review ID — табуляцию). Контракт запрещает whitespace-only identity, но `btrim(text)` без второго аргумента удаляет только обычный пробел. Табуляция/перевод строки остаются непустым text. PK/FK и raw↔core equality не исправляют это: они сохраняют одинаковый неверный ключ.

**Impact:** сборка принимает запрещённого контрактом «покупателя» или review identity. На нынешних Olist MD5 IDs такое изменение не доказано; это конкретный разрыв type/key precheck для нового входа.

Минимальная проверка семантики:

```sql
SELECT btrim(E'\t') = '', btrim(E'\n') = '';
-- Оба false: не whitespace-only guard.
```

Источник — [PostgreSQL 16, btrim](https://www.postgresql.org/docs/16/functions-string.html). Этот PG-repro reviewer не исполнял.

**Точечная рекомендация:** определить допустимый whitespace predicate (например, `key ~ '^[[:space:]]*$'`) и одинаково применить его в precheck/DDL/checks для обязательных identities, не trim-ить сохраняемые исходные значения. Добавить TAB/LF negative case. Категорию с известным пустым PT-именем по существующему контракту не запрещать этой общей правкой.

## Что подтверждено и почему это не только statement counts

- Прочитаны все 29 pinned inputs: raw→core DDL и casts, quality, фактические mart/answer expressions, psql wrapper/reset, invariant generator, manifest verifier и lifecycle/rollback/fingerprints. Дополнительно сверены исходные `scripts/init/02_raw_ddl.sql`, `scripts/load_raw.py`, оба manifest-пина, tests, документация и задание. Имена `product_name_lenght`/`product_description_lenght` сохранены; единственный rename времени позиции — `shipping_limit_date`→`shipping_limit_at`. Все восемь loader mappings совпали с header/table в W11 pin.
- Reviewer независимо повторил **93 checks в DuckDB 1.5.2**, static19, bash syntax, make dry-run и plan16 — exit0. Python14 — результат родительского повторного прогона, источники тестов прочитаны; reviewer не повторял создающие временные файлы unittest вне writable зоны. Это разделение записано в evidence.
- **Новый ограниченный runtime-result W14 проверен по артефактам**, а не предположен: [pg-smoke.json](pg-smoke.json), [pg-smoke.md](pg-smoke.md), PostgreSQL 16.15, `2026-10-28T09:57:18.471172+00:00`—`09:57:20.446111+00:00`. CLI exit0; 16 scenarios = 4 positive/warning passes + 12 correctly detected failures, не «16 отрицательных ошибок». Семь stage hashes и 14 пересекающихся input hashes before/after совпали с review manifest. Тестовые schemas после внешнего rollback отсутствовали. Reviewer сам PG не запускал.
- Проверены конкретные ожидаемые diagnostics W14: NaN/invalid integer/NULL key — P0001 precheck; duplicate item/review pair — 23505; dangling product — 23503; calendar gap, компенсирующие +10/−10, потеря review text, удалённый/подменённый item key и multiplicity — 23514 с требуемыми именами нарушений. В compensating case общая сумма сохранена, но order-level/value проверки сработали: это содержательная проверка, а не один count.
- `run_checks()` генерирует 201 правило (16×11 +25), с двусторонним EXCEPT ALL типизированных значений, кратностью и NULL profiles, FK и денежными срезами. Broken check сам становится error, а не PASS. R2 показывает точечный пропуск в этой в целом сильной схеме проверки.

## Сильные стороны и сохранённые контраргументы

1. **Grains и identity.** `fact_order` не зависит от наличия children; LEFT JOIN customer context приводит dangling identity к NOT NULL/FK error, а не к потере заказа. Item/payment/review хранят собственные ключи. Buyer — `customer_unique_id`; unused contexts сохранены отдельно; адрес остаётся на context/order. Q4 считает buyers с заказами, а не безусловно размер dim_customer.
2. **Money/coverage.** `v_orders` агрегирует items/payments/reviews независимо, потом соединяет по order_id. No child, all NULL, partial и measured zero различаются; `order_gmv` требует обе компоненты каждой позиции, payment имеет свой знаменатель. Четыре payment-presence класса независимы от суммы. Exact/`>0.01`/`=0.01` используют собственные matching counts/net/absolute sums. Нули суммы пустого выбранного mismatch-set явно определены паспортом и сопровождаются comparable/non-comparable counts — это не скрытая подмена неизвестного payment нулём.
3. **Категории и календарь.** `unknown` отделён от `pt:<исходное имя>` без collision, untranslated category не теряется. Domain включает неиспользуемые переводы. Дневной календарь строится через integer date arithmetic по всем source timestamp roles; Q1 получает distinct месяцы и явные границы 24-месячного окна. Дополнительные даты dimension не добавляют лишние Q1 месяцы.
4. **Отзывы.** Сохраняются все пары и все пять payload-полей. На конфликтном ID `v_review` возвращает conflict и NULL payload, а варианты доступны отдельно. Pair/ID/order weights имеют собственные numerator/denominator/excluded counts. Не выбирается произвольный latest/min текст; out-of-range score сохранён и виден отдельно. Это обоснованный implementation default, не окончательное человеческое решение о весе dashboard.
5. **Сборка.** `-X -1 -v ON_ERROR_STOP=1 -w`, раскрытие include до DB-connect, `search_path=pg_catalog,pg_temp`, ISO/UTC session settings и fail-fast advisory lock дают разумный каркас. Reset перечисляет только owned objects, использует RESTRICT и не пишет raw. DROP внутри одной транзакции должен откатываться при последующей SQL-ошибке; это правдоподобно по коду, но **psql wrapper/late rollback ещё не исполнены**. Пользовательская `.psqlrc` и password prompt исключены. Потеря связи около commit честно отделена от доказанного rollback.
6. **Raw reload.** В коде нет защиты от некооперирующего loader; это прямо отражено в runbook. Операторская эксклюзивная фаза и `RWB_RAW_RELOAD_PAUSED=1` — явная предпосылка, а не автоматическое обнаружение. Поэтому отсутствие LOCK TABLE само по себе не объявляю скрытым дефектом; предъявлять конкурентную безопасность как уже доказанную нельзя.
7. **Контроль и ответы.** Build не подгоняется под 13 221 498.11: pinned controls вынесены. W10/W11 восемь CSV hashes совпали; audit-manifest SHA реально равен `8afb8691d866ef5f5ed465eb9111df521408e1b3d84408d5f0c03337477312c3`. Но это проверка pins, не live raw. Q1 counts, Q2 counts, Q3 item/payment means, Q4 windows именованы раздельно. Контроли считают из core/mart. Q6–Q10 в прочитанном `tasks.md` ещё отсутствуют; отсутствие выдуманных ответов корректно.

## Runtime-gates до заявления «сдаваемая модель работает»

1. Исправить R1 и выполнить маленький PG-тест CSV→raw verifier; затем доказать pinned eight-CSV↔raw EXCEPT ALL equality на одном endpoint и остановленной генерации. Совпадение manifest вместо этой проверки не принимается.
2. Исправить R4 и выполнить настоящий `make build` на чистом core/mart из полного Olist raw. Сохранить SQL/server versions, кодовые и input hashes, exit/log, число и результат invariant rules; вывести Q1–Q5 из модели и отдельный `control` после binding. Это требует разрешённого по ресурсам стенда; preflight78 не обходить.
3. Выполнить повторный build и сравнить content/DDL fingerprints; намеренно дойти до `W11_INJECTED_LATE_FAILURE_AFTER_ALL_CHECKS` через реальный psql entrypoint и проверить восстановление **предыдущей committed модели**, raw и definitions. Savepoint rollback в 16 tiny cases доказывает другое свойство и не заменяет этот тест.
4. Проверить RESTRICT при внешней зависимости и согласованный raw-reload protocol на изолированном стенде в обоих порядках. Произвольная TRUNCATE/DDL гонка не покрывается обещанием REPEATABLE READ. Не испытывать её на общей рабочей базе.
5. Закрыть R2/R3/R5 адресными сценариями; обновлённые байты получают новые hashes и scoped re-review. Не переводить все 201 правила в «полное покрытие любых ошибок» только по количеству.

W14 не исполнял `00_schemas.sql`, `model/build.sql`, shell-wrapper, pinned raw-inputs, Olist controls, committed rebuild/late rollback, permissions matrix или reload races. Указанные gates после W14 остаются открыты. Никаких новых VM/демонов/dependencies/full fixtures этот reviewer не запускал; сохранённый W14 runtime не трогал.

## Что говорить жюри на этом checkpoint

«Мы сохраняем четыре независимых уровня событий: заказ, позицию, платёж и связь отзыва с заказом. Покупателя узнаём по customer_unique_id, а адрес храним как контекст заказа. Суммы детей считаем до соединения; неизвестная сумма остаётся неизвестной, ноль остаётся измеренным нулём. Наши малые тесты PostgreSQL уже обнаруживают искусственные потери, дубли и компенсирующие денежные ошибки. Полную сборку Olist и ответы из core пока не объявляем проверенными: закрываем замечания независимого review и проходим отдельные input-binding/rebuild/rollback gates. Направление модели принято; параметры метрик из подробного пакета не выдаём за 17 отдельных согласований».

Не заявлять сейчас: «полная модель прошла PostgreSQL», «полный rollback/rebuild проверен», «контрольные цифры уже получены из core», «все runtime gates закрыты» или «все смысловые параметры утверждены человеком».

## Точный input snapshot

Manifest SHA256: `750e53104571050dd336f4a03aeaf5d19f28fed332a111ab25f45edbf25515fa`.

| Файл | SHA256 при начале review |
|---|---|
| `Makefile` | `f7c2ac69813d122789f5b6f98151362d49497d936013e8e17d0b326d9c873706` |
| `answers/control.sql` | `8856e395c3afbfd2c769c47ced9fe23667b7312bf6582045640fcb6feebc890d` |
| `answers/payment_reconciliation.sql` | `20ce8db0e5178de9fdddbe06155339ec5ccacf8f0ecebb6187609ea2560dd7e2` |
| `answers/q01.sql` | `3b5a2f8a8d7bccc312d94b1394a296f3d58b128933d756a145fd25f20afe00f1` |
| `answers/q02.sql` | `238458b3f2a51c080d22ea46275dabcbe17408c4140cae74b97c559faf84b6c7` |
| `answers/q03.sql` | `ca3a5fffbcf740a35cf07e19f9dc4a7aeed32e3d851b097e521e7a6d33402e6e` |
| `answers/q04.sql` | `84efc278d2d9ab17be03b1c8e8ff3324b8d285a1446dd8b2c73765f4518bb471` |
| `answers/q04_window.sql` | `d332d0fc0e9c80c4953cb8c043f565ba033af09d99b0a4e93e33c0229391da5f` |
| `answers/q05.sql` | `b600f36c685ea74014b99497f0fd349eb3e999649005f2dd20ad1939b6b4f77e` |
| `answers/review_weights.sql` | `d855be39f7717e3016bfd1ee158ed7d3ca67c27a8d8b6faa683b79340cede0e8` |
| `model/00_schemas.sql` | `ef09205e8b59c32c19bd7caec41b396655946695b8c9ed481d3aac479557981d` |
| `model/05_typecheck.sql` | `34fc2a829a9983eaee47714884a8640258fc9c9b5b71af3e7b1af024a9d91157` |
| `model/10_dims.sql` | `f7aa80dcc9b8cb11ecd997259638cabaabebfb3f959950d3910c472d0b29aa39` |
| `model/20_facts.sql` | `1d9ca47499c18429546cd4cc2cbf3e3668a1a7ba667faf62eba65067f107a234` |
| `model/30_quality.sql` | `1a3ce9264e7ed92fda96c27f9b9d0c170393be81dc90711d721dce8f2b2a08ab` |
| `model/40_mart.sql` | `7b3060c4d375f764b5933c04246799b694adbf8c73a625d8a91736fb6a7b6bc2` |
| `model/50_answers.sql` | `abe0684d5c21e531fb28802e9750f4ec07f33c10a59abb292909f0a3c00b2138` |
| `model/90_checks.sql` | `fc1dbe0b902cecdefb8447f0498681b0eb59566966df8ccee985cdb178816ca2` |
| `model/CONTRACT.md` | `6a5fe6c2b1dd64db9accb6a8363a9bdb26973da1000060d3c1151c466de008af` |
| `model/build.sql` | `c3398e357d2f2a7100d5532e48c5d4a7ea450098acb0266db83889c2d01e5c59` |
| `scripts/build-model.sh` | `ef527345f1b91f84c5759aa7a17cbe97b36c3572f472f00d9229058017c282b6` |
| `scripts/input-manifest.py` | `3da62ab650f071e4d3e86201768cd7c7b2bcd4b7ad1a56117977cbf5791738d8` |
| `scripts/verify-model.py` | `f4e6751be51580db19e9dc7bba5494e7b9664c7f443b234478614c7f5ca24c11` |
| `tests/model/fingerprint.sql` | `39995edc49d0c5f471fd52179f9c4e9180eb25751f7143290dd8d604ff07adde` |
| `tests/model/fixtures/assert-base.sql` | `e91763223e528a04977d79272ad6abad4566ee006b8e512dd094520cb93c2518` |
| `tests/model/fixtures/base.sql` | `dd70d0046d4c09fd269ddde08ecbdc8898d5fbeb4e5fa22128e4b03318a72c0a` |
| `tests/model/fixtures/cases.json` | `996287daccc47fdba95f4dd199cab35d5a4d82438b831348fb26ed11ad7cbeea` |
| `tests/model/rollback.sql` | `7ff18076507bb60ab191990b90c8435ad88cf7a64540deeed8053baad209561e` |
| `tests/model/validate-lifecycle.sh` | `c6b045191158ce91ef95af8f05b8ac4d68459e42f5b013aaa147ee8fa95998bb` |

Все значения из колонки совпали с expected в root manifest; итоговая сверка и любые поздние изменения фиксируются в `astra-evidence.json.final_files` / `input_drift`.
