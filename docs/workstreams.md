# Работы, владельцы и общий контекст

Repository: `kiruha355/rwb_hak` · proposal branch: `proposal/mput-agent-workflow-20261028`
Base SHA: `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e` · snapshot UTC: `2026-10-28T10:11:06Z`

> Статус: карта задач нашей рабочей группы; общекомандное размещение реестров и архитектура не утверждены этой записью.

Эта карта описывает нашу группу задач. Иные команды, машины и ветки могут работать параллельно; отсутствие записи не доказывает отсутствия работы. Владелец записи определяется её автором/согласованной ролью, а не названием используемого клиента.

Цель кейса: объяснимая и воспроизводимая аналитическая модель Olist, ответы из модели, готовность к новым вопросам и защита по всей рубрике. Реализация запущена по прямому поручению пользователя: Текущие зоны W-08…W-16 уточнены передачей W-12 → W-15 и root-reserved fixes. Требования/research и обратимые defaults доступны; факт записи файлов не подтверждает runtime PASS.

| ID | Задача и owner | Зона файлов | Статус | Следующий шаг |
|---|---|---|---|---|
| W-01 | Интеграция, публикация и root R1–R5 fixes · корневой координатор | Общий Git index/публикация + точные root-reserved fix paths ниже | in_progress | Сам владеет адресными Astra R1–R5 fixes; эти файлы прежним агентам не возвращаются. Публиковать проверенные порции без рутинных пробуждений. |
| W-02 | Требования и асинхронный registry · координатор требований | AGENTS.md, CLAUDE.md, docs/workstreams.md, docs/ideas.md; свой каталог исследований | in_progress (registry); requirements candidate done | Поддерживать ownership и агрегировать handoff. Корень не будить рутинными квитанциями; без новых панелей/исследований. |
| W-03 | Объяснение команде · автор explainer | explainer.html, docs/decision-log.md | in_progress | Поддерживать понятный разбор данных/операций/результатов и оценку существенных вариантов по всем7критериям; без повторной общей анкеты. |
| W-04 | Интернет-исследование · координатор исследований | research/README.md, research/internet-2026-10-28/ | done (research slice) | Финальный корпус/3 review/синтез: b7495d66faebee5ba9b07d829caee019a6e76fdf; 85 manifest hashes сверены. 102 records, 162 dispositions, 18 selected findings; новые интенты и перенос в модель — отдельная работа. |
| W-05 | Проверка данных · независимый аналитик | research/data-audit-2026-10-28/ | in_progress | Проверить 8 CSV, ключи, кардинальности, деньги и baseline; не выдавать raw baseline за результат core. |
| W-06 | Бриф и пакет решений перед реализацией · автор implementation-brief (Codex / Sol) | docs/implementation-brief-20261028.md, docs/implementation-brief-20261028.html | ready_for_review (final brief); publication W-01 | Финальный ready сообщён координатором; W-01 публикует цельную пару. До publication SHA не считать опубликованным или runtime PASS. |
| W-07 | Подготовка dev-окружения (Codex / Sol) | docs/dev-environment-20261028.md, scripts/dev-check.sh, requirements-dev.txt | blocked (live dev); artifacts ready_for_review | Три файла переданы W-01 и frozen владельцем; offline check exit0, обычный check exit3 на Docker по отчёту владельца. После снятия локальных runtime-блокеров выполнить runbook/checks; DB/model не проверены. |
| W-08 | Модель и сущности · модельный поток | model/CONTRACT.md, model/10_dims.sql, model/20_facts.sql, docs/model.md | ready_for_review (code); runtime pending | Код передан по handoff; независимый review W-13 и последующие правки в своей зоне. Без DB/core runtime PASS. |
| W-09 | Сборка и type/quality prechecks · поток build | Makefile, model/build.sql, model/00_schemas.sql, model/05_typecheck.sql, model/30_quality.sql, scripts/build-model.sh | ready_for_review (code); runtime pending | Исходный handoff передан; docs/build-runbook.md теперь root-reserved. Прочие файлы не менять за W-01; runtime отдельно. |
| W-10 | Mart, ответы и варианты метрик · поток аналитики | model/40_mart.sql, answers/**, docs/metric-definitions.md | ready_for_review (code); runtime pending | Исходный handoff передан; model/50_answers.sql теперь root-reserved. Открытые бизнес-трактовки сохраняются; runtime отдельно. |
| W-11 | Проверки и input manifest · поток validation | scripts/input-manifest.py, tests/model/** кроме root-reserved paths ниже | ready_for_review (prior handoff); root fixes reserved | Исходный handoff передан; verify-model.py, test_verify_model.py, cases.json, 90_checks.sql, fingerprint.sql, model-validation.md теперь только W-01. Не возвращать эти файлы агенту. |
| W-12 | Завершённая артефактная работа · прежний артефактный агент | docs/submission/** — полностью передано W-15 прямым поручением пользователя | closed by ownership handoff → W-15 | W-12 не продолжает запись в переданную зону. Завершение работы по handoff не означает runtime PASS; дальнейший пакет и питч ведёт W-15. |
| W-13 | Независимый review цельной интеграции · Astra gpt-6-astra high, serviceTier default / non-Fast | research/implementation-review-20261028/astra-review.md, research/implementation-review-20261028/review-input.json | in_progress | Закрепить input SHA и проверить цельный код; писать только два review-артефакта, не W-08…W-12 и не PG smoke W-14. Независимые потоки продолжаются. |
| W-14 | Малые PG16 smoke checks · Sol xhigh, serviceTier priority | research/implementation-review-20261028/pg-smoke* | in_progress | Проверить PG16 на предустановленном сервере без VM/установок, закрепить метод/input/results; heavy операция при guard78 не разрешена обходом. |
| W-15 | Единый пакет и питч2мин · Sol xhigh Fast, продолжение W-12 | README.md, docs/submission/** | in_progress | Сначала docs/submission/checkpoint-now.md и checkpoint-now.html; далее единый пакет. Малые цельные ready-порции публикуются прямо в main, независимо от Astra review. |
| W-16 | HTML UI и read-only core/mart exporter · Sol xhigh Fast | dashboard/** | in_progress | Vanilla HTML, demo/import/export small checks; экспорт только core/mart, без Streamlit/heavydeps, временных зависимостей и серверов. Малые ready-порции прямо в main; индекс W-16 не пишет. |

Общие места этой версии: [идеи](ideas.md), [исследования](../research/README.md), [правила](../AGENTS.md). Журнал решений и explainer добавляются отдельной проверенной порцией. Актуальный ownership реализации — таблица W-08…W-16 и root-reserved список; разрешение работы не означает готовность.

## Присоединение и передача

1. Fetch; прочитай правила и актуальные записи, проверь изменившиеся чужие ветки.
2. Запиши ID/цель/owner/repository/branch/base SHA/owned paths/status/UTC/next step. При совпадении зоны сначала согласуй границу.
3. Перед изменением общего реестра согласуй writer. Опубликуй свой результат в своей ветке; не меняй чужую версию без review.
4. Передай проверенные и непроверенные части, команды, блокеры, точный следующий шаг и remote commit. Если общего стандарта ещё нет, явно назови документ предложением.

Статусы: proposed → in_progress → ready_for_review → accepted/done; blocked обозначает конкретную зависимость. Accepted относится к решению/объёму, done — к выполнению с evidence. Устаревшая запись не означает разрешения перезаписать файлы.

Шаблон записи: `ID | цель | owner | repository | branch | base SHA | owned paths | status | UTC update | checks/results | unchecked | blockers | next step | published SHA`.

## W-06 · Контекст и границы

- Repository: `kiruha355/rwb_hak`; рабочая branch: `main` общего checkout.
- Input/base: `origin/main` на `1939068295d7203a15cbb0a1ab5d407caca90f58`.
  Локальный HEAD при сверке: `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`.
- Owner: автор брифа перед реализацией (Codex / Sol); status: `ready_for_review` (final brief), публикацию выполняет W-01.
- Начало сверки по запросу владельца: `2026-10-28T09:01:00Z`.
- Owned paths: `docs/implementation-brief-20261028.md` и
  `docs/implementation-brief-20261028.html`. Заявленные зоны не пересекаются
  с W-01…W-05 по проверенным refs; общие реестры и explainer не входят в W-06.
- Next: финальный ready брифа сообщён координатором; W-01 публикует цельный пакет
  с причинами/альтернативами, схемами и acceptance. Бриф сам по себе не approval всех спорных метрик. Более поздним прямым поручением
  реализация уже запущена по обратимым defaults ниже; W-06 не является gate для независимых потоков.
- Git index/commit/push W-06 не меняет. Готовый результат планируется публиковать
  в `proposal/implementation-brief-20261028` от свежего main через согласованного writer;
  создание/публикация этой ветки данной записью не утверждаются.
- UTC update записи writer: `2026-10-28T09:05:10Z`; публикация исходной записи: proposal 6b0629de8abd557e8f882863db251511a3b041db / idea-bank aa6e1d16c7efc6212ba09fdc092aeea3aeb9229e; текущая редакция передаётся отдельно.

## W-07 · Контекст и границы

- Repository: `kiruha355/rwb_hak`; branch общего checkout: `main`.
- Input/base: `origin/main` на `1939068295d7203a15cbb0a1ab5d407caca90f58`;
  локальный HEAD: `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`.
- Owner: подготовка dev-окружения (Codex / Sol); start: `2026-10-28T09:06:39Z`;
  status: `blocked` для живого dev-стенда; артефакты: `ready_for_review`.
- Owned новые paths: `docs/dev-environment-20261028.md`, `scripts/dev-check.sh`,
  `requirements-dev.txt`. Зона не пересекается с двумя файлами W-06.
- Next: безопасная проверка/подготовка уже выбранных PG16/Python/psql, runbook и runtime checks.
  `requirements-dev.txt` закрепляет единственную psycopg2-binary для существующего loader;
  точная версия определяется и проверяется владельцем, здесь не выдумывается.
- `scripts/dev-check.sh` — только read-only offline/daemon/DB checks, без bootstrap,
  загрузки raw, изменения core/mart, модели и бизнес-SQL. Индекс/commit/push W-07 не трогает.
- Частные пути окружения, состояние машины, ресурсные ограничения и локальные разрешения
  остаются в ignored local context; статус этой записи не означает готовность DB/runtime.
- План публикации готового handoff: `proposal/dev-environment-20261028` через W-01;
  repo-visible SHA фиксируется после проверки/публикации, здесь пока pending.
- UTC update registry writer: `2026-10-28T09:11:35Z`.

### W-07 · Передача безопасной подготовки

- UTC status update: `2026-10-28T09:16:05Z`. Три owned файла подготовлены и переданы W-01;
  owner больше не меняет их до согласованного следующего шага. SHA256 сверены writer
  с локальными файлами, без запуска скрипта.
- По handoff владельца: offline read-only check — exit0 (8 CSV/toolchain/config/driver),
  обычный check — exit3 на Docker. Это отчёт владельца, не повторный runtime-test writer.
- Блокер живого dev-стенда: локальное ресурсное ограничение и недоступный Docker daemon.
  Частные значения/пути и локальные разрешения остаются в local context/runbook.
- Следующий шаг: после наблюдаемого снятия блокеров выполнить предварительную проверку
  и штатные действия из [runbook](dev-environment-20261028.md), затем `scripts/dev-check.sh`.
  Публикация файлов сама по себе не делает live dev/DB/model проверенными или done.
- Артефактный SHA: `e4c085c7f25df6447b5d3365707a11eda649bc54`, публикация реестра сверена.
  Runtime-статус остаётся blocked, публикация не делает DB/model проверенными.

## W-08…W-12 · Исходная реализация и последующие уточнения ownership

- Прямое поручение: реализация уже идёт. Общий checkout branch `main`, локальный HEAD
  `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`; доступный input `origin/main`:
  `1939068295d7203a15cbb0a1ab5d407caca90f58`. Перед интеграцией проверить affected refs.
- Исполнение: до четырёх Sol xhigh Fast и одного артефактного агента. Review цельного
  кода — Astra high non-Fast. Это запись текущего распределения, не запуск агентов
  данным writer и не обязательный общий харнесс. Review не блокирует независимые потоки.
- Уже явно разрешённые обратимые implementation defaults: detail constellation,
  натуральные ключи, buyer_unique и адрес заказа, review pairs без потерь, независимая
  агрегация детей, numeric precheck, раздельные build/check/control, именованные
  варианты спорных метрик. Это не17 человеческих approvals; повторно их не запрашивать.
- Прямые user rules: raw неизменен; ответы из модели; полный scope; код пишут агенты;
  unknown не равно0. Следовать фактическим входным именам/контрактам, не переименовывать
  исходные поля ради shorthand из этой записи.
- Открытые populations/windows, review weight, late/deadline aggregation, область/
  инструмент dashboard и smoothing явно обозначать. Обратимый default не означает,
  что любая бизнес-трактовка окончательно выбрана человеком.
- Один writer каждой указанной зоны; пересечение или изменение owned paths согласовать.
  Исходные зоны были разделены; актуальная передача W-12 → W-15 и root-reserved
  исключения ниже имеют приоритет. W-15/W-16 от root fixes независимы.
- Не запускать новые панели/исследования. Корневому координатору передавать только
  реальный blocker, конфликт ownership либо цельный ready-пакет с проверками.
  Квитанции и обычные registry updates агрегировать, не будить корневой тред.
- Для `docs/implementation-brief-20261028.md` и `.html` финальный ready теперь сообщён;
  публикацию цельной пары выполняет W-01. Прежний hold до ready выполнен, не заменён
  автоматическим одобрением архитектуры или runtime.
  Наличие файлов не означает runtime PASS, review PASS или готовность живого стенда.
- UTC update ownership writer: `2026-10-28T09:27:12Z`; публикация текущего обновления pending в агрегированном handoff.

## W-13 · Review интеграции

- Repository: `kiruha355/rwb_hak`; input main:
  `1939068295d7203a15cbb0a1ab5d407caca90f58`; локальный HEAD общего checkout:
  `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`.
- Owner: независимый reviewer Astra `gpt-6-astra`, reasoning `high`, serviceTier `default`
  (non-Fast); status: `in_progress`. Это запись назначенного review, не новый запуск writer.
- Owned paths: только `research/implementation-review-20261028/astra-review.md` и
  `research/implementation-review-20261028/review-input.json`. Прежний широкий prefix
  сужен для явного разделения с W-14 `pg-smoke*`. Текущие зоны W-08…W-12 уточнены передачей W-15 и root-reserved fixes ниже.
- Root review manifest должен закрепить конкретный вход и изменения после него.
  Не блокировать независимые потоки ожиданием review; изменённые после snapshot места
  требуют адресной проверки, старый verdict не относится автоматически к новым байтам.
- По handoff родитель повторил: 14 unittest, 93 DuckDB offline checks, static19files,
  bash syntax, make dry-run, fixture plan16cases — exit0. W-02 эти прогоны не повторял;
  соответствие именно текущему SHA-срезу требует test/review manifest.
- DB/core runtime pending. Offline check, существование файла и review не означают
  PostgreSQL build или готовность живого окружения. W-07 live остаётся blocked до нового evidence.
- W-06 final ready сообщён, публикация — W-01. Приостановленные диагностики
  и внешние стенды без прямого указания не возобновлять.
- Дополнительный read-only SHA-срез writer: `research/requirements-panel-2026-10-28/implementation-current-input.json`,
  SHA256 `1005aead0035a59687148a59753321bc2bd1af1f74f4fdfb81e5609b18899ed3`, 58 файлов W-08…W-12, UTC `2026-10-28T09:47:56Z`.
  Он не заменяет owned root manifest W-13; исходники/тесты writer не менял и не запускал.
- Registry update UTC: `2026-10-28T09:47:56Z`; pending для агрегированной публикации без рутинной квитанции корню.

## W-14 · PG16 smoke и актуальный checkpoint

- Repository: `kiruha355/rwb_hak`; source main:
  `1939068295d7203a15cbb0a1ab5d407caca90f58`; локальный HEAD общего checkout:
  `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`.
- Owner: Sol xhigh, serviceTier `priority`; status: `in_progress` по handoff координатора.
  Это регистрация уже назначенной задачи, не запуск агента данным writer.
- Owned paths: `research/implementation-review-20261028/pg-smoke*`. W-13 owns только
  `astra-review.md` и `review-input.json`; пересечения этих зон нет.
- Scope: малые PG16 smoke checks на предустановленном сервере, без VM/установок.
  Если понадобится heavy операция, отказ guard78 не обходить. Результаты/source/runtime
  закрепляет W-14; запись in_progress не означает PostgreSQL/core PASS.
- Актуальный пользовательский checkpoint: **2026-10-28 10:30 UTC /13:30 МСК**.
  Он заменяет прежний ориентир10:01 UTC, остаётся промежуточным; полный scope сохранён.
- W-06 готов по handoff; W-01 выполняет публикацию. Новых панелей/анкет/рутинных
  пробуждений корня нет; квитанции и этот registry-ready агрегируются.
- UTC update registry writer: `2026-10-28T09:53:34Z`.

## W-15 / W-16 · Продолжение полного scope

- Прямое поручение пользователя: оба потока `in_progress`, Sol xhigh Fast;
  выполняются независимо от Astra review. Готовые осмысленные порции с проверками
  публикуются прямо в `main`; для общего checkout согласованный writer Git index сохраняется.
- W-15 продолжает завершённый W-12: единственный текущий writer `README.md` и
  `docs/submission/**`. Сначала `docs/submission/checkpoint-now.md` и
  `docs/submission/checkpoint-now.html`, затем единый пакет и питч2мин. Это не новый
  сокращённый scope. Файлы W-12 не имеют двух одновременных writers.
- W-16 — только `dashboard/**`: vanilla HTML UI плюс read-only exporter из core/mart.
  Нет Streamlit, heavy dependencies, временных зависимостей/серверов; W-16 не пишет index.
  Next: HTML/demo/import/export small checks. Unknown не подменять0; наличие UI не runtime PASS.
- Input W-16 указан владельцем: `aca34f5b693b794fc2a0ea8c2623293b462b6089`; при fetch наблюдался main
  `f174bee0e81beafadfe96d73c8bcb9dbffdec1d3`; локальный HEAD общего checkout:
  `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`. Пин входа не подменяется более новым ref молча.
- Исходный запрос update W-16: `2026-10-28T10:10:00Z`; время записи writer указано ниже.

## Root-reserved Astra R1–R5 fixes

Следующие пути закреплены за W-01, не возвращать их прежним W-09/W-10/W-11:

- `scripts/verify-model.py`
- `tests/model/test_verify_model.py`
- `tests/model/fixtures/cases.json`
- `model/90_checks.sql`
- `model/50_answers.sql`
- `tests/model/fingerprint.sql`
- `docs/model-validation.md`
- `docs/build-runbook.md`

Новые root fix evidence в `research/implementation-review-20261028/` также ведёт W-01;
он фиксирует имена новых файлов до записи. Это не передача существующих
`astra-review.md`/`review-input.json` W-13 или `pg-smoke*` W-14. Нельзя молча расширить
ownership на их результаты. W-15 `README.md`/`docs/submission/**` и W-16 `dashboard/**`
от этих fixes независимы. Открытые трактовки/уровни доказательств по-прежнему помечаются.
- Registry writer UTC update: `2026-10-28T10:11:06Z`. Публикационный ready агрегируется; рутинное сообщение корню не отправлено.
