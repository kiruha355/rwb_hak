# Реализация истории категорий

Статус: реализация и bounded PG16 verification завершены в изолированной feature
ветке `t3/category-history-implementation`. Merge main, PR, HTTP routing,
deployment и официальная публикация пересмотра не выполнялись.

Owner: implementation sub-agent Sol. Orchestrator worktree:
`/Users/a/.t3/worktrees/rwb_hak/t3-b2abfe76`.
Вход: published `t3/integrate-q6-q10-marts` at
`aab62d7a59f196be051df12466fb21c0da4659b9` (включает `2e8eff9`).
Это база feature, не новый main; начальный checkout был `2f0a8de`.

## Ownership

Зарегистрирован до реализации отдельным commit
`501822191032ee17e16297681277e72ac605031b`:

- `model/history/**`;
- `model/00_schemas.sql`, `10_dims.sql`, `20_facts.sql`, `40_mart.sql`,
  `90_checks.sql`, `build.sql` — только механизм истории и его проверки;
- `tests/model/history/**`;
- этот handoff;
- `scripts/build-model.sh` — только history/release wiring.

`app/**`, `dashboard/**`, `docs/submission/**`, общий checkout/index и другие
агенты не менялись. Семь public Q6–Q10 relations сохранили имена и поля.

Код механизма: `36af5acb2b120c08a3106a0bdd5351e7aad06d85`.
Runner и evidence: `4a6af76f962824023443bb014be05a2dae7ff3e0`.
Сопроводительный документ может быть отдельным последним commit; точный head
публикации сообщается вместе с handoff. SHA256 23 исполняемых исходников сверены
с [summary.json](../tests/model/history/evidence/accepted-pg16/summary.json).

## Поведение

Сохраняемая схема `history` содержит product baseline с NULL business start,
append-only events обоих scopes, release manifests, taxonomy/labels, стабильные
item bindings и pinned result digests. `core/mart` — проекция выбранного release.
Обычный rebuild по умолчанию выбирает начальный `original-v1`, не latest event
или latest release. Выбор другого выпуска явный: `RWB_REPORT_RELEASE=R1`.
`core.model_release` показывает материализованный выпуск; `history.report_result`
появляется только после успешного build. Сохранённый manifest без result ещё не
означает успешную материализацию или официальную публикацию.

Source event identity + canonical payload определяют idempotency/conflict.
Seller override имеет приоритет перед product event; `unset_override` возвращает
product fallback, `set unknown` оставляет unknown. Равная boundary внутри scope,
missing event identity, незамкнутая correction chain, fork и несовпадение
scope вызывают ошибку. Никакой Olist as-of из текущей категории не выводится.
Events без сопоставимого времени остаются evidence; observed-since требует
явного naive purchase clock contract.

Extension наследует прежние bindings и taxonomy. Удаление/изменение parent raw
payload и поздние order/item/payment/review строки закрытого периода запрещены.
Restatement — отдельный ID с явным пересчётом. Source helpers не устанавливают
реальные полномочия автора/официального издателя.

До DROP проверяется точная raw business generation: все 8 таблиц, hashes строк
с multiplicity, без loader `_loaded_at`/`_source_file`. Восстановление старого
выпуска на несовместимом текущем raw останавливается, прежний core сохраняется.
После сборки проверяются bindings/версии, scope, taxonomy, детализация mart и
категориальные суммы. Hashes всех 13 answer relations Q1–Q10 закрепляются первым
успешным build и сравниваются при повторном build того же release.

Подробный SQL interface, clock/boundary semantics, rollback и восстановление —
[model/history/README.md](../model/history/README.md). Нужен dump всей `history`
плюс exact raw generation/CSV artifacts. Hashes без bytes недостаточны. Внешний
artifact store, production authorization/API, backup schedule не создавались.

## Проверки

Установленный PostgreSQL 16.15 (Homebrew), собственный временный cluster:
Unix socket в `/tmp`, TCP выключен, shared_buffers=16MB, max_connections=5,
max_parallel_workers=0. Не использовались localhost:5432, рабочий marketplace,
реальные raw/CSV, Docker, установки и чужие процессы. Полный Olist запрещён
известным guard78 и не запускался.

[Воспроизводимый runner](../tests/model/history/verify-small-pg16.py):

```bash
python3 tests/model/history/verify-small-pg16.py /tmp/rwb-category-evidence-new
```

Каталог evidence должен быть новым. Runtime удаляется после остановки только
созданного этим процессом сервера. [Evidence](../tests/model/history/evidence/accepted-pg16/summary.json):
PASS, UTC `2026-10-28T14:05:31.232556+00:00`, 182 записанных шага/проверки,
включая ожидаемые отказы. Это не 182 независимых business assertions.

Проверено фактическим SQL:

- Clean build, rebuild, generic invariants и entrypoint ответов Q1–Q10 на
  исходном 10-order fixture. Raw fingerprints до bootstrap и после совпали.
- Все исходные поведенческие assertions Q6–Q10 на 16-order fixture; в памяти
  адаптирован только loader stages для нового lifecycle. Файл assertions не менялся.
- A→B→rebuild и seller isolation: R0 `A=300`; extension R1 `A=340, B=30`.
  Backdated correction не меняет original R1; отдельный restatement даёт
  `A=240, B=130`. Старые version IDs и bindings остаются прежними.
- Half-open boundary before/at, product + seller precedence, unset, observed-only
  policy, explicit unknown, возврат A с новой identity. Эти ветви проверены и
  resolver SQL, и полным build на восстановленной копии с 7 будущими заказами.
- Exact event/release retry, conflicting identity, missing clock/event,
  correction scope/fork/chain, ambiguity, immutable source и sealed manifest.
  Source checksum corruption обнаружена в транзакционных negative tests.
- Одна buyer identity с SP/01000 и RJ/20000 в разных customer_id. Новые
  customer contexts/заказы MG/30000 и rebuild сохраняют обе старые географии.
  Исправление прежнего customer context вызывает raw-generation mismatch и rollback.
  Это доступные prefix/city/state; полного почтового адреса в Olist нет.
- Cold restore только raw+history (без core/mart), затем build R1: fingerprints
  содержимого/определений core/mart и Q1–Q10 совпали. Синтетический dump сохранён
  отдельно как [source-restore.sql](../tests/model/history/evidence/accepted-pg16/synthetic-source-restore.sql).
- Ошибка после всех checks откатывает модель, candidate release/bindings/result
  и сохраняет ранее committed source. Raw mismatch перед DROP оставляет прежний
  model; поздние item, empty order, payment и изменение taxonomy требуют restatement.
  Late restatement с дополнительной позицией: `A=240, B=137`, original не изменён.
- Семь frontend relations имеют ровно поля FRONTEND-HANDOFF; их SQL исходники
  не менялись. Свой сервер остановлен, временный runtime удалён.

Общие самопроверки: `model/90_checks.sql`, `model/history/04_checks.sql`.
Конкретные regression values находятся в runner и fixture assertions; pinned
Olist `answers/control.sql` не запускался и не использован как общий invariant.

## Пределы и вопросы интеграции

Полный Olist lifecycle, CSV→live raw equality, реальные Q6–Q10 результаты,
performance/growth, конкурентные некооперирующие writers и production privileges
не проверялись. Данные доказательств исключительно синтетические. Storage первого
варианта — полные row-hash manifests и bindings на release; оптимизация требует
измерений. Canonical JSONB format закреплён PG16, major upgrade требует проверки.

Технического design blocker не осталось. Для реального включения нужны факты от
владельца источника: кто вправе подавать product-scope changes, какой business
clock у событий, где сохраняются точные source bytes каждого выпуска и кто
публикует официальный restatement. Реализация не выдаёт рекомендацию ASTRA или
выполнение SQL за user approval. Archive/HTTP routing/deployment не выполнялись.

ИИ: SQL, runner и этот handoff подготовлены Sol. Рекомендация category-history
проверена как инженерный вход; из неё взяты сохраняемый source, оба scopes и
immutable release binding, без предложенного production API/store/role deployment.
Проверка результата — фактический private PG16 и сохранённые assertions/hashes.

Перед публикацией выполнен `git fetch origin`; diff относительно `aab62d7`
не содержит app, dashboard, submission, answers или изменения public Q6–Q10 SQL.
