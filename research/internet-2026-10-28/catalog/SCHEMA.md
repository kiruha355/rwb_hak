# Формат каталога и статусов

`all-findings.jsonl` — исходный широкий пул: одна строка на finding, не на уникальный источник. Поля: finding_id, direction, research_questions, url, author, source_type, primary, accessed_at, commit_ref, observation, evidence_locator, evidence_path, application, limitations, implementation, license, confidence, status. Terra corpus добавляет inference, verification_method, task, acceptance_check. Поля `_source_file/_source_line/_stage/_package` задают provenance записи; `_validation` не означает автоматическое принятие.

`primary`, `confidence` и `status` сохраняют самооценку исследователя. Окончательные рекомендации — `synthesis/selected-findings.jsonl`; все исходные reject/unresolved остаются. Наличие URL или успешный HTTP не доказывает прочитанный текст, runtime или правильность применения.

`search-operations.jsonl` — записи поиска/open/API/локального чтения: query, language, tool, timestamp, purpose, results_opened, outcome, gaps плюс provenance. Время может быть только интервалом сессии; не восстанавливается с выдуманной точностью. Число записей не равно числу уникальных поисковых запросов.

`review-matrix.jsonl` связывает каждый finding с диспозициями reviewer, sources, задачей и proposed check. `adopt_now` — рекомендация после согласования; `later` — условная зависимость; `reject` — конкретное утверждение или перенос; `unresolved` — недостаточное evidence. Review может отклонять плохой pattern, одновременно рекомендуя проверку против него. Это не голосование и не human approval. Разрешение расхождений — `synthesis/disagreements.md`.

Evidence types разделяются: документ/статическое чтение; собственный CSV-расчёт; fixture; DB/raw; core/mart; UI/runtime. В этой работе последние четыре не подтверждались. Относительные пути разрешаются от корня repo, если поле evidence_path начинается с `research/`; остальные locators объяснены конкретным report. Remote refs и hashes позволяют повторить чтение на другой машине; приватные run IDs не нужны.
