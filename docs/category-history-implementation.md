# Реализация истории категорий

Owner: implementation sub-agent Sol, выделенный orchestrator worktree
`/Users/a/.t3/worktrees/rwb_hak/t3-b2abfe76`, branch `t3/b2abfe76`.
Вход: published `t3/integrate-q6-q10-marts` at
`aab62d7a59f196be051df12466fb21c0da4659b9` (включает `2e8eff9`).
Это база feature, не новый main; начальный checkout был `2f0a8de`.

Ownership до реализации:

- `model/history/**`;
- `model/00_schemas.sql`, `10_dims.sql`, `20_facts.sql`, `40_mart.sql`,
  `90_checks.sql`, `build.sql` — только механизм истории и его проверки;
- `tests/model/history/**`;
- этот handoff;
- `scripts/build-model.sh` — только history/release wiring.

`app/**`, `dashboard/**`, `docs/submission/**`, общий checkout/index и другие
агенты вне scope. Семь public Q6–Q10 relations и их поля сохраняются.
Нет новых серверов приложения, services, installs, raw/CSV writes или production
запусков. Единственный runtime проверки — собственный маленький временный PG16,
Unix socket, shared_buffers=16MB; никаких запросов на localhost:5432.

Статус: implementation in progress. Полный Olist запрещён guard78 и не запускается.
