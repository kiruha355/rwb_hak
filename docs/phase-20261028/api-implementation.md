# API Q6–Q10

- Owner: implementation sub-agent, Codex / GPT-6.1 Sol; checkout
  `/Users/a/.t3/worktrees/rwb_hak/t3-1b244690`.
- Coordinator: `mcp:ff50ef29-ba22-48ce-836b-d046b08d3a24`.
- Base: `aab62d7a59f196be051df12466fb21c0da4659b9`, published
  `t3/integrate-q6-q10-marts`; main snapshot
  `bbbfab8a67aa9c9920c250dc4f638e66ffbc4fc4`.
- Proposal branch: `t3/api-answers-block-b-aab`; no main merge or PR.
- Owned paths: `app/api/block-b.js`, small mount in `app/api/server.js`,
  `app/api/tests/block-b*`, this document. Shared registry is not edited.
- UTC start: `2026-10-28T14:04:40Z`; status: `in_progress`.

## Contract agreed with UI

Read-only `GET /api/answers-block-b`; top-level response:
`q6.rows`, `q7.rows`, `q8.rows`, `q9.states`, `q9.methods`, `q10.rows`,
`q10.coverage`, `meta.scope`. Rows retain exact columns of
`model/55_answers_block_b.sql`, variant enum values and NULL. Existing
`/api/answers` Q1–Q5 stays intact. Missing views or database errors must fail
the request, never become successful empty arrays.

## Boundaries and pending checks

Use only the seven named mart views from the pinned stage 55. No model, history,
UI, deployment or shared runtime changes. Full Olist DB lifecycle is still
pending. Previous small PG16 and CSV experiments do not prove full DB PASS.
Guard 78 forbids heavy local fixtures and installs; use existing tooling for
small focused checks. Any new tiny fixture will be labelled synthetic.

Implementation, exact types, validation results and publication comparison will
be recorded here before handoff.
