# W-16 · HTML dashboard ready for review

Repository `kiruha355/rwb_hak`, branch `main`, UTC `2026-10-28T10:18:48Z`.
Owner W-16 (Codex / Sol); owned paths **dashboard/** only.
Status **ready_for_review**, not published/done. Local shared dirty HEAD stayed
`2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`; accepted model input
`aca34f5b693b794fc2a0ea8c2623293b462b6089`. Last fetch observed remote main
`fb7c5f3d55d6e83b93be592b226d58d6f66c53a3` (fetch verified before `2026-10-28T10:18:48Z`).
No index/commit/push/checkout/pull/reset/merge performed.

## Ready paths

- `dashboard/index.html`: complete standalone HTML/CSS/JS; no server/CDN/deps.
- `dashboard/sample/export_data.py`: read-only existing core/mart → JSON and optional
  standalone HTML; uses already installed psycopg2 in W-07 venv.
- `dashboard/sample.json`: 24 clearly synthetic demo orders, never Olist controls.
- `dashboard/README.md`: run/export/data contract/limits and AI authorship.
- `dashboard/checks.js`: injected DOM checks, not part of production HTML runtime.
- `dashboard/sample/check_export.py`: small reproducible offline exporter checks.
- `dashboard/qa-results.json`: actual methods and results, explicit pending gates.
- `dashboard/evidence/desktop-1100.png`, `dashboard/evidence/mobile-390.png`:
  final clean screenshots from html_preview; full HTML shown via html_render.
- `dashboard/HANDOFF.md`: this review/publication handoff.

## Result and verification

Three compact stories: service (primary), sales, quality/coverage. Month volume
and late chart, customer state comparison with late denominators, review-pair
histogram, seller revenue comparison. Date/state filters, whole snapshot,
calendar-day/timestamp late selector, chart selection → order table → original
dates/items/all review pairs. Formulas/sources and manifest expand on request.
NULL differs from zero; uncompleted cohorts do not count as quality failures.
No carrier blame, buyout inference, damage estimate or hidden review ranking.

PASS: **25 DOM checks at 390 px and 25 at 1100 px**, including keyboard chart
selection, tab arrows, focus return from dialog, primary filters, seller drill,
unknown money, no-delivered tail, empty input/slice, invalid import retention,
File API import without server/fetch, and rejection of missing exported items.
PASS: **4 offline Python exporter tests**, script injection escaping and JSON/HTML
roundtrip, full decimal precision/nonfinite protection, SELECT/no raw/no LIMIT.
PASS: unique DOM IDs, inline JS `node --check`, exporter `--help` without DB.
Visual review: clean service 390/1100, sales and quality 728; no console errors.
Only temporary files/cache created by these small checks were removed.

**Pending:** exporter SELECT execution on a real PostgreSQL model; real Olist
JSON/HTML export and UI E2E; full raw binding, controls and build lifecycle.
No DB connection, setup/reload, Docker, installation or heavy run was attempted.
This handoff does not declare production/DB success or ten completed answers.

## SHA-256 for publication review

| Path | SHA-256 |
|---|---|
| dashboard/index.html | `862c174cca9fe26b14fa5f2cef107465f0205aa5c7e62ff4a4b508c9a05a8ee7` |
| dashboard/sample/export_data.py | `274f3f95d355d2bd7c24a88d9703a2bc611940e89132c3acac2d469ccc22ce5b` |
| dashboard/README.md | `7c0c586bab4a4d0f7fdeb938b2d2fd53098c84df2284e60a30b7c27ac439510b` |
| dashboard/sample.json | `7885c32bcce137f59681e7242421af29881a6bab094179402057e7377f63a6d9` |
| dashboard/checks.js | `d1a248f21ec73fb1306434984e680bef5b18d55b372ee6c8b569f2e4a1372d5f` |
| dashboard/sample/check_export.py | `843524f2715e98b5f9bcdf16c44ee3427f7ac8042687a6bc67f4008d8749a0d0` |
| dashboard/qa-results.json | `950089619cb05d3e83957e65883ddbc5d0a7fc93157d3e788a023c714018f106` |
| dashboard/evidence/desktop-1100.png | `2d8aeb445be1661bc2bd7d98f66c3e5feb4920573a6439d4ad98c44231413422` |
| dashboard/evidence/mobile-390.png | `8253cd9d7630b59b68bc24665390b7dd5d6327b4e77902cc4d78d792d1495027` |

W-01: review and publish these exact paths as one small coherent slice. Registry,
explainer, decision log, worker/model code and W-15 artifacts were untouched.
After model availability, follow `dashboard/README.md` export command; do not
mark `exported_not_validated` as full source validation.
