# Handoff: паспорта метрик Q6–Q10

- Owner: implementation sub-agent Codex, checkout `/Users/a/.t3/worktrees/rwb_hak/t3-deb9dae5`.
- Base: `aab62d7a59f196be051df12466fb21c0da4659b9` (`t3/integrate-q6-q10-marts`); требования организаторов `558f0f6a38110acc9fcf4386a7e53ece973aedf5`.
- Owned paths: `docs/metric-definitions.md`, `model/56_metric_passports.sql`, `docs/phase-20261028/metric-passports-handoff.md`.
- Scope registration UTC: `2026-10-28T14:01:47Z`; status: `ready_for_integration`; update UTC: `2026-10-28T14:04:00Z`.
- Границы: без изменений history, `model/00`, `10`, `20`, `40`, `90`, `build` и общего registry; без полного Olist DB lifecycle, установок и чужих runtime.

## Результат

14 новых паспортов в `56_metric_passports.sql` используют существующие 12
столбцов `mart.metric_definitions` и уникальные имена `q06_`–`q10_`. Это
описания вычислений из `55`, не цифры ответов. Документ описывает гранулярность,
популяции, формулы, время и окно, знаменатели, NULL, единицы, аддитивность и
происхождение; ссылки на все четыре эксперимента отличают наблюдения и
рекомендации от решения человека. U-15 сохранён. Устаревшее утверждение об
ожидании вопросов и всех проверок PG16 заменено текущим состоянием.

## Интеграция

После приёма этой ветки ответственный за build добавляет **в** `model/build.sql`
строку `\ir 56_metric_passports.sql` непосредственно после
`\ir 55_answers_block_b.sql` и до `\ir 90_checks.sql`. Это SQL-фрагмент без
транзакции и raw reads; `40` должен уже создать и заполнить таблицу. Фрагмент
не предназначен для повторного вызова поверх той же таблицы: полный rebuild
сначала пересоздаёт её через существующий `00`/`40`. Никаких изменений `00`,
`40`, `90` или history этим вкладом не требуется. После включения обновить
фразу в начале `docs/metric-definitions.md` о том, что stage ещё не подключён;
проверить wiring-тесты и обновить ожидания содержимого `metric_definitions`,
если они фиксируют прежний набор. На будущей версии history и на итоговой
ветке интегратора необходимо заново проверить зависимости и совместную сборку.

После `git fetch origin` main был `bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4`,
интеграционная remote-ветка — точно `aab62d7`. В main ещё нет `55`, поэтому
прямое перенесение этих трёх файлов в main без интеграционного дерева не
создаёт работающий набор Q6–Q10. На момент проверки `40` на main, `aab62d7` и
локальном `t3/category-history-implementation` имел один blob
`dff764c6a4b002e75ddd27ad538abf794affb263`; `build` history-ветки совпадал
с `aab62d7` (`a310e09e3409e1d18bfac3deb984dd458b28f93d`). Это наблюдение о
коммитах, не проверка незакоммиченного или будущего кода history-агента.

## Проверено и осталось

- PG 16 на собственном временном Unix-socket сервере с `shared_buffers=16MB`:
  выполнены фактические DDL и INSERT из `40` до `CREATE VIEW mart.v_orders`,
  затем `56`; 34 существующие + 14 новых записей, все ограничения NOT NULL и
  PRIMARY KEY прошли. Дважды пересозданы schema и таблица; упорядоченный
  digest строк совпал (`6fc25fdbd9f36ebd06b3482318f9177b`). Сервер остановлен,
  его временный каталог удалён. Это тест контрактов таблицы, не вызов wrapper
  и не проверка метрик на фактических данных.
- Воспроизведение на **собственном пустом** PG16: выполнить `CREATE SCHEMA mart`,
  часть `model/40_mart.sql` до `CREATE VIEW mart.v_orders`, затем
  `psql -X -v ON_ERROR_STOP=1 -f model/56_metric_passports.sql`; запрос
  `SELECT count(*), count(*) FILTER (WHERE name ~ '^q(06|07|08|09|10)_') FROM mart.metric_definitions;`
  должен вернуть `48 | 14`. Для rebuild повторить после пересоздания schema.
- `git diff --check`; проверить опубликованную ветку и её точный SHA после push.
- Не проверены включение в общий build/90, интеграция с будущими history
  изменениями, full Olist lifecycle и actual core results. PG16 fixture на
  `aab62d7` и CSV oracle документированы в фазовом README и не повышаются до
  full-data PASS. Следующий шаг: интегратор подключает stage, проверяет малый
  совместный rebuild и позже сравнивает полный core с oracle на разрешённом
  стенде.
