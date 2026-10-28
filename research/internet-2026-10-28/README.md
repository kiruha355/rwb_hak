# Internet research RWB — подробный индекс

Дата: 2026-10-28. Input: kiruha355/rwb_hak / 2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e. Синтез: Sol xhigh.
Статус: **полный исследовательский цикл завершён локально; финальная публикация pending**. Это рекомендации, не принятая архитектура или DB/model PASS.

## Результаты

- [Итоговый русский отчёт](final-report.md).
- [18 сильнейших результатов/кандидатов](synthesis/selected-findings.md) и [JSONL](synthesis/selected-findings.jsonl).
- [Полный P0/P1/P2 backlog](backlog.md), включая what-not-to-do и вопросы источнику.
- [Покрытие 8 тем, языков, источников и пробелов](coverage.md).
- [Все 102 исходные записи](catalog/all-findings.jsonl), [138 logged operations](catalog/search-operations.jsonl), [162 reviewer dispositions по всем IDs](catalog/review-matrix.jsonl), [schema/status semantics](catalog/SCHEMA.md), [source→task→check matrix](catalog/task-matrix.md).
- [Разрешение разногласий Sol](synthesis/disagreements.md), [сопоставление main fc84](synthesis/compare-main-fc84.md).
- [Проверенные CSV/source наблюдения](orchestrator/validated-early-findings.md), [регламент и candidate organizer](orchestrator/requirements-targeted-check.md).
- [Manifest файлов и hashes](publication-manifest.json).

## Корпус и review

3 Gemini3.8Flash medium orientation → quality gate → 7 GPT6.1Terra high packages → 3 независимых GPT6.1Terra xhigh review → Sol synthesis. Модель широкого поиска изменена по явному выбору пользователя после concrete evidence ошибок, а не из-за capacity. Приватный технический audit не входит в общие результаты.

[Программа вопросов](orchestrator/research-program-v1.md), [исходные RQ](orchestrator/research-questions-v0.md), [intake](intake.jsonl), [quality gate](orchestrator/orientation-quality-gate.md). Исходные claims Gemini сохранены полностью в каталоге; original orientation reports/локальные технические заметки не нужны для чтения итоговых proof и могут не входить в portable публикацию.

| Пакет | Материал |
|---|---|
| B01 | [Olist provenance / identity / reviews / categories](corpus/01_olist_identity/report.md) |
| B02 | [Деньги / comparator / fanout / populations](corpus/02_money_reconciliation/report.md) |
| B03 | [Grains / keys / normalized core versus constellation](corpus/03_model_choices/report.md) |
| B04 | [PostgreSQL16 build / assertions / raw consistency](corpus/04_pg_build_checks/report.md) |
| B05 | [Метрики / время / dashboard examples](corpus/05_metrics_time_dashboard/report.md) |
| B06 | [Рост / история / indexes / engines](corpus/06_growth_evolution/report.md) |
| B07 | [Реальные pinned SQL/dbt проекты и counterexamples](corpus/07_real_implementations/report.md) |
| R1 | [Correctness и самостоятельная CSV проверка](reviews/01_correctness/report.md) |
| R2 | [Моделирование и воспроизводимость](reviews/02_model_repro/report.md) |
| R3 | [Жюри / метрики / dashboard / стратегия](reviews/03_jury_value/report.md) |

Во всех package folders — findings, actual search/source logs, reports и compact evidence. `adopt_now` означает рекомендацию, не человеческое принятие. Отклонённое и разногласия сохранены. Матрица строк/источников не означает буквальный охват интернета; EN преобладает.

## Переносимость и границы

Пути repo-relative, внешние источники закреплены по ref/section/locator; свой reproducer читает CSV или pinned URLs. Полные CSV, зависимости, runtime dumps, секреты и приватные agent transcripts не публикуются. Рабочий интерфейс коллег — Git и эти файлы; конкретный харнесс не требуется.

Выполнены source/static/CSV checks; DB/Docker/services/model/fixture/UI/benchmark не запускались. Исходники и чужие зоны не менялись, собственных commit/push/merge нет. Семь candidates и ранние наблюдения опубликованы на 266bdfabc8707393a7e88c35411d22fa5a4983d3 ветки idea-bank; исторические фразы локальных report о публикации относятся к их моменту/входному SHA. Финальные файлы этой порции не считаются published до возвращённого remote SHA.

Новые intents добавляются в этот исследовательский центр без удаления прежних вариантов. Scope полный амбициозный; checkpoint около10:01UTC промежуточный, не конечный deadline. Незнание инструмента человеком не основание упрощать реализацию: её пишут агенты, объяснения/совместные решения ведёт согласованный owner.
