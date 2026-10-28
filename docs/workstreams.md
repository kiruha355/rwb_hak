# Работы, владельцы и общий контекст

Repository: `kiruha355/rwb_hak` · proposal branch: `proposal/mput-agent-workflow-20261028`
Base SHA: `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e` · snapshot UTC: `2026-10-28T09:16:05Z`

> Статус: карта задач нашей рабочей группы; общекомандное размещение реестров и архитектура не утверждены этой записью.

Эта карта описывает нашу группу задач. Иные команды, машины и ветки могут работать параллельно; отсутствие записи не доказывает отсутствия работы. Владелец записи определяется её автором/согласованной ролью, а не названием используемого клиента.

Цель кейса: объяснимая и воспроизводимая аналитическая модель Olist, ответы из модели, готовность к новым вопросам и защита по всей рубрике. Требования и финальный research опубликованы как кандидаты; W-06 готовит пакет решений, W-07 — dev-окружение. Работающая модель этим реестром не подтверждается.

| ID | Задача и owner | Зона файлов | Статус | Следующий шаг |
|---|---|---|---|---|
| W-01 | Публикация нашей версии · координатор версии | Ветка предложения и review готовых порций | in_progress | Сохранить кандидат, проверить remote SHA и дать ссылку коллегам. |
| W-02 | Требования и правила · координатор панели | AGENTS.md, CLAUDE.md, docs/workstreams.md, docs/ideas.md; свой каталог исследований | done (requirements candidate) | Опубликованный U08: be7c3ec61aa64c95f785f6da16fe43520e2b0ac9, 7 hashes сверены. Общая архитектура не утверждена; текущие registry updates публикуются отдельными порциями. |
| W-03 | Объяснение команде · автор explainer | explainer.html, docs/decision-log.md | in_progress | Выпустить понятную первую версию и первые вопросы человеку; файлы не входят в этот ранний пакет. |
| W-04 | Интернет-исследование · координатор исследований | research/README.md, research/internet-2026-10-28/ | done (research slice) | Финальный корпус/3 review/синтез: b7495d66faebee5ba9b07d829caee019a6e76fdf; 85 manifest hashes сверены. 102 records, 162 dispositions, 18 selected findings; новые интенты и перенос в модель — отдельная работа. |
| W-05 | Проверка данных · независимый аналитик | research/data-audit-2026-10-28/ | in_progress | Проверить 8 CSV, ключи, кардинальности, деньги и baseline; не выдавать raw baseline за результат core. |
| W-06 | Бриф и пакет решений перед реализацией · автор implementation-brief (Codex / Sol) | docs/implementation-brief-20261028.md, docs/implementation-brief-20261028.html | in_progress | Сверить синтез v2 с финальным research; собрать причины, альтернативы, схемы и acceptance. Координация не означает approval архитектуры или запуск разработки. |
| W-07 | Подготовка dev-окружения (Codex / Sol) | docs/dev-environment-20261028.md, scripts/dev-check.sh, requirements-dev.txt | blocked (live dev); artifacts ready_for_review | Три файла переданы W-01 и frozen владельцем; offline check exit0, обычный check exit3 на Docker по отчёту владельца. После снятия локальных runtime-блокеров выполнить runbook/checks; DB/model не проверены. |

Общие места этой версии: [идеи](ideas.md), [исследования](../research/README.md), [правила](../AGENTS.md). Журнал решений и explainer добавляются отдельной проверенной порцией. Исполнитель model/SQL этим снимком ещё не назначен.

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
- Owner: автор брифа перед реализацией (Codex / Sol); status: `in_progress`.
- Начало сверки по запросу владельца: `2026-10-28T09:01:00Z`.
- Owned paths: `docs/implementation-brief-20261028.md` и
  `docs/implementation-brief-20261028.html`. Заявленные зоны не пересекаются
  с W-01…W-05 по проверенным refs; общие реестры и explainer не входят в W-06.
- Next: сопоставить synthesis v2 с финальным research, изложить причины/альтернативы,
  схемы и acceptance. Это пакет решений до реализации, не approval архитектуры,
  не изменение модели и не запуск разработки.
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
- Публикационный SHA артефактов фиксируется после handoff W-01 отдельно от runtime-статуса.
