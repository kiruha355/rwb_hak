# Индекс исследований группы RWB / Capibara

Repository: [kiruha355/rwb_hak](https://github.com/kiruha355/rwb_hak). Обновлено UTC: 2026-10-28T08:58:30.162389+00:00.
Owner: исследовательская группа / Sol synthesis. Это **candidate общего реестра**, не объявленный consensus всей команды. Общие правила и идеи коллег сопоставляются отдельно.

## Текущий результат

Полный цикл ориентирование → широкий корпус → 3 независимых review → синтез **завершён локально**. Итоговые файлы готовы к публикации; их remote SHA ещё не возвращён. Архитектура/метрики/инструменты остаются рекомендациями до решения человека. Реализация не урезается из-за знаний участников; код пишут агенты, понимание развивается через explainer.

- [Итоговый отчёт](internet-2026-10-28/final-report.md).
- [18 выбранных результатов и кандидатов](internet-2026-10-28/synthesis/selected-findings.md), [полный backlog P0/P1/P2](internet-2026-10-28/backlog.md).
- [Покрытие и пробелы](internet-2026-10-28/coverage.md), [исходный пул](internet-2026-10-28/catalog/all-findings.jsonl), [решения трёх reviewer](internet-2026-10-28/catalog/review-matrix.jsonl), [разрешение разногласий](internet-2026-10-28/synthesis/disagreements.md).
- [Фактические ранние CSV/source проверки](internet-2026-10-28/orchestrator/validated-early-findings.md), [сопоставление нового main](internet-2026-10-28/synthesis/compare-main-fc84.md).
- [Publication manifest](internet-2026-10-28/publication-manifest.json): точные paths/hashes и excluded audit. Новые относительные ссылки этой порции доступны в локальном checkout и после публикации всей manifest-порции; на старом snapshot они могут отсутствовать.

## Provenance и опубликованные части

Input проекта: main `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`, материалы 2026-10-28. Olist ref: `d9e49802f3e92d09ee94ab9ccc5e457f207a8959` (2022-03-04); CSV hashes/counts в evidence. Последний просмотренный новый main: `fc84ecf98be8405058bc60453cc61af321b1b666`, добавляет только `docs/idea-synthesis.md`; baseline code/data не изменены. Fetch не означает merge и не обещает вечной свежести.

| Работа / owner | Method / intent | Status / результат | Пути и следующий шаг |
|---|---|---|---|
| Internet research, Sol + исследователи | Личное чтение; 3 Gemini medium orientation; по явному выбору пользователя 7 Terra high corpus; 3 Terra xhigh review; Sol source/CSV checks | `completed_local / ready_for_publication`: 102 исходных records (24+78), 162 review dispositions по всем 102 IDs, 18 selected рекомендаций | [Подробный индекс](internet-2026-10-28/README.md), final-report/backlog/catalog. Следующий шаг — публикация manifest и решение команды, затем инженерные acceptance checks. |
| Семь corpus packages, Terra high | Olist/provenance; деньги; modeling; PG16; metrics/dashboard; evolution; actual code | **Опубликованы как candidates** на [266bdfab](https://github.com/kiruha355/rwb_hak/tree/266bdfabc8707393a7e88c35411d22fa5a4983d3/research/internet-2026-10-28/corpus), не implementation PASS | В папках report/findings/search-log/evidence. Итоговые review/synthesis — новая порция, публикация pending. |
| Requirements panel, отдельный owner | Требования, противоречия, пользовательские цели и правила | Candidate контракт опубликован на proposal branch; shared approval не заявлен | [Контракт на 7f8f538](https://github.com/kiruha355/rwb_hak/blob/7f8f538f4b25130572d105ff128f67223f6a75a6/docs/task-contract.md). Назначенная область `research/requirements-panel-2026-10-28/`; не предполагаем публикацию всех внутренних memo. |
| Общий банк идей коллег | Сравнение идей и research разных участников | Материал для обсуждения, не авторизация всех пунктов | [idea/ на опубликованном ref](https://github.com/kiruha355/rwb_hak/tree/266bdfabc8707393a7e88c35411d22fa5a4983d3/idea), [09](https://github.com/kiruha355/rwb_hak/blob/266bdfabc8707393a7e88c35411d22fa5a4983d3/idea/09-mput-ideas.md), [10](https://github.com/kiruha355/rwb_hak/blob/266bdfabc8707393a7e88c35411d22fa5a4983d3/idea/10-mput-research.md). Не перетирать registries других writers. |

## Как интерпретировать evidence

`verified` относится к конкретному методу/снимку; `unverified` — исходный claim; `unresolved` — недостаточное evidence; `rejected` — указанное утверждение или перенос; `stale` — изменился релевантный input/ref. `adopt_now` у reviewer — recommendation после согласования, не human approval и не выполненная реализация.

Здесь подтверждены CSV/static/source observations. DB/raw equality, core/mart, fixture/rollback, UI и benchmark не запускались. Семь numeric/semantic проверок не заменяют тест модели. Исходный профиль и новый синтез main содержат уточняемые claims; причины расхождений, переезды и as-of не выдумываются.

Для новой записи нужны intent, owner, repository/branch/input ref+date, method, validation status, actual result, relative paths/remote URLs к proof, coverage/gaps и next check. Личные paths, приватные run IDs и machine-specific настройки не служат рабочим интерфейсом коллег. Несколько процессов не меняют один shared Git index одновременно; локального writer согласуют участники, разные checkout публикуют свои ветки по Git protocol с fetch/ref/ownership/diff.
