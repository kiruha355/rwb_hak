# Реестр идей — предложение нашей группы

Repository: `kiruha355/rwb_hak` · proposal branch: `proposal/mput-agent-workflow-20261028`
Base SHA: `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e` · snapshot UTC: `2026-10-28T09:11:35Z`

> Статус: реестр кандидатов нашей группы для сравнения с реестрами коллег; выбранная архитектура и общекомандное размещение этим файлом не утверждаются.

Writer этой порции — координатор панели требований (W-02 в [карте работ](workstreams.md)).
Присылай записи writer, не перетирай общий файл параллельно. Это реестр, не разрешение
реализовать архитектуру. Статусы идей: `idea`, `proposed`, `accepted`, `rejected`, `superseded`.
`accepted` требует основания/ссылки на явное решение в [журнале](decision-log.md).
Отклонённое сохраняем с причиной; выполнение учитывается в workstreams с evidence и SHA.
Подробные статусы исследований — в [research/README.md](../research/README.md);
explainer объясняет эти записи и ссылается на них, не ведёт второй независимый реестр.

| ID / идея | Problem / польза | Owner исследования · status | Evidence / границы | Next check / решение |
|---|---|---|---|---|
| I-01 · Раздельные уровни фактов | Убрать размножение сумм и сохранить детали для новых вопросов | Панель требований · `proposed` | [Handout](../hack-context/hackathon-students/docs/handout.md), [tasks](../hack-context/hackathon-students/docs/tasks.md), D-01 журнала; новые CSV/multiplicity evidence приведены в IR-01; actual raw/core ещё не проверены | Сравнить детальный связный core и созвездие фактов, проверить grain/ключи; решение команды. Реализация не назначена. |
| I-02 · Паспорта метрик | Явные совокупности, окна, знаменатели, доставка и деньги | Панель требований · `proposed` | Tasks Q1–Q5 и [profiling](profiling.md); профиль не равен результату из core, D-02 | Уточнить Q1/Q2 order counts, Q3 comparator и окна; показать альтернативы и проверку. |
| I-03 · Учёт качества без молчаливых исправлений | Не потерять строки/смысл при аномалиях и дедупликации | Панель требований + researcher · `proposed` | Profiling, [intake](../research/internet-2026-10-28/intake.jsonl), IR-02/03/04; D-03. Новые CSV evidence не доказывают причины расхождений или DB/core PASS. | Проверить payload отзывов, population/NULL/comparator денег, сохранность ключей и дат; политика — решение команды. |
| I-04 · Область дашборда: продажи или доставка | Один пользователь и конкретное действие вместо набора графиков | Панель требований, исполнитель не назначен · `idea` | Handout: концепция без обязательного UI; D-04 | Сравнить пользователей/решения/доступность полей; выбор команды и паспорт каждой метрики. |
| I-05 · Версия CSV и manifest | Воспроизводимость при изменении внешнего источника | Researcher · `proposed` | [download_data.sh](../scripts/download_data.sh), V-01 журнала; pinned source/hash evidence опубликованы в research; raw equality и scope CSV licence остаются отдельными проверками | Подтвердить URL/ref/хеши и политику повторной загрузки, не менять raw автоматически. |
| I-06 · Поэтапное развитие PostgreSQL | Обосновать рост измерениями, стоимостью и SLA | Researcher + панель, исполнитель не назначен · `idea` | Handout / PDF рубрика стратегии; D-04; benchmark не выполнен | Сценарии нагрузки, bottleneck, метрики перехода и сравнение вариантов. Не выдумывать универсальный предел строк. |

Ни одна из I-01–I-06 пока не отмечена accepted/rejected: получены предложения explainer,
нужны исследования и совместный выбор. Полные варианты и последствия — в decision-log/explainer;
здесь только индекс кандидатов этой версии; единое общекомандное размещение ещё сравнивается с реестрами коллег.

## Финальный research: IR-01…08

Финальный пакет опубликован на `b7495d66faebee5ba9b07d829caee019a6e76fdf` proposal-ветки:
85 manifest hashes сверены writer, 102 исходных записи покрыты 162 review-позициями,
shortlist содержит 18 результатов/кандидатов. Это проверка публикации/структуры;
содержательные решения команды и DB/core/runtime PASS отсюда не следуют.

[Итог](../research/internet-2026-10-28/final-report.md) ·
[18 findings](../research/internet-2026-10-28/synthesis/selected-findings.md) ·
[backlog](../research/internet-2026-10-28/backlog.md) ·
[coverage](../research/internet-2026-10-28/coverage.md) ·
[disagreements](../research/internet-2026-10-28/synthesis/disagreements.md).
Источник добавлений: [handoff JSONL](../research/internet-2026-10-28/handoff/ideas-additions.jsonl).
Относительные ссылки проверены на указанном publication SHA; перенос пакета в другие ветки
проверяется отдельно. `rejected` ниже относится к неподтверждённому research claim,
а не к решению команды отказаться от проекта/возможности. Гипотеза может оставаться unresolved.

| ID / идея или claim | Problem | Owner · status | Evidence / validation boundary | Next check |
|---|---|---|---|---|
| IR-01 · Раздельные grains и безопасный join | Независимые дети одного заказа размножают суммы; order mart не заменяет detail. | Research synthesis; implementation per agreed ownership · `proposed` | [selected-findings.md, S03](../research/internet-2026-10-28/synthesis/selected-findings.md); [sol-independent-check.json](../research/internet-2026-10-28/orchestrator/evidence/sol-independent-check.json) — CSV multiplicity and source semantics checked; DB/model proposed | 0/1/many child fixture и сверка отдельных totals из выбранной core. |
| IR-02 · Exact comparator с coverage и одной population для count/sum | Пара366/−1819.51 не воспроизведена одним из проверенных фильтров. | Research/data modelling · `proposed` | [results.json](../research/internet-2026-10-28/corpus/02_money_reconciliation/evidence/results.json); [csv-check.json](../research/internet-2026-10-28/reviews/01_correctness/evidence/csv-check.json) — Independent CSV/Decimal:639/−1819.51 exact;366/−1818.84 >0.01 | Сверить actual raw/core; указать population/sign/tolerance/NULL и missing children. Исходный SQL коллег запросить у владельца, не приписывать метод. |
| IR-03 · Отклонённый как факт claim: Причины расхождений и survey/NPS story как факты | Несколько Gemini повторили причинные объяснения без первичных событий. | Research verification · `rejected` | [orientation-quality-gate.md](../research/internet-2026-10-28/orchestrator/orientation-quality-gate.md); [disagreements.md](../research/internet-2026-10-28/synthesis/disagreements.md) — Rejected as established claims; hypotheses can remain unresolved | Только новый первичный ledger/survey specification может подтвердить причины; не выводить их из совпавших сумм или FD. |
| IR-04 · Review pair versus entity+bridge и явный вес | Dedup review_id теряет associations, mean зависит от единицы наблюдения. | Research/model and metric contract · `proposed` | [observed.json](../research/internet-2026-10-28/corpus/01_olist_identity/evidence/observed.json); [csv-check.json](../research/internet-2026-10-28/reviews/01_correctness/evidence/csv-check.json) — 99224 unique pairs,0payloadconflicts on snapshot; representation choice open | Round-trip pairs/payload, future conflicting FD/NULL/ties, mean ID/association/order; получить решение о contract. |
| IR-05 · Отклонённый как факт claim: Tu Nguyen полностью теряет review payload | По одному aggregate mart ошибочно оценён весь проект. | Research source audit · `rejected` | [disagreements.md](../research/internet-2026-10-28/synthesis/disagreements.md); [code-locators.md](../research/internet-2026-10-28/reviews/02_model_repro/evidence/code-locators.md) — Pinned staging selects text/timestamps; global loss claim refuted | Проверять полный detail→mart lineage и лицензию перед переносом; source MIT attribution corrected. |
| IR-06 · Regression controls по manifest; общие build invariants отдельно | Зашитые контрольные числа могут ломать корректную сборку после вброса. | Model/check agents; source idea-synthesis author · `proposed` | [compare-main-fc84.md](../research/internet-2026-10-28/synthesis/compare-main-fc84.md); [backlog.md](../research/internet-2026-10-28/backlog.md) — Static design comparison; no DB execution | Изменить fixture input и pinned manifest: относительные проверки проходят, regression oracle обновляется осознанно. |
| IR-07 · Shipping/late proxy без причинной вины | Order carrier timestamp нельзя автоматически приписать отдельному seller; timely handoff не доказывает carrier blame. | Metric/dashboard research · `proposed` | [compare-main-fc84.md](../research/internet-2026-10-28/synthesis/compare-main-fc84.md); [report.md](../research/internet-2026-10-28/corpus/05_metrics_time_dashboard/report.md) — Field-grain limitation checked; new author counts not independently verified | Описать proxy/grain/coverage и запросить item/seller handoff events; не выводить causal blame/lost revenue из association. |
| IR-08 · Полный ambitious scope с объяснением и общим metric contract | Прежние приоритеты/оценки часов могут превратиться в необоснованный запрет UI/semantic/AI вариантов. | Team decision and implementation agents; explainer owner · `proposed` | [backlog.md](../research/internet-2026-10-28/backlog.md); [final-report.md](../research/internet-2026-10-28/final-report.md); [compare-main-fc84.md](../research/internet-2026-10-28/synthesis/compare-main-fc84.md) — Direct user scope recorded; tools/model choices remain proposals; full ambitious scope уже прямо принят пользователем (U-06), конкретные interfaces/contract ещё proposed | Согласовать полный сценарий и interfaces; выполнять независимые ветки параллельно, доказать metric/permission/result consistency; checkpoint is intermediate. |

IR-01 развивает I-01; IR-02/06 — I-02/I-03/I-05; IR-04 — I-03; IR-07 — I-04.
Существующие I-01…06 сохранены. Существенные варианты выносятся человеку с пользой,
риском и проверкой по всем семи критериям рубрики; нерелевантному явно «прямого влияния нет»
с причиной. Исследовательский отбор не заменяет такой выбор.
