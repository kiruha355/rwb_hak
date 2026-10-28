# Независимая adversarial-проверка

- Owner: test sub-agent, Codex Sol; checkout `t3-61e94ad3`.
- Repository: `kiruha355/rwb_hak`.
- Execution input: `aab62d7a59f196be051df12466fb21c0da4659b9`, published `t3/integrate-q6-q10-marts`.
- Checkout base: `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`, branch `t3/61e94ad3`.
- Publication: separate branch `t3/adversarial-20261028`; target tree based on pinned input, isolated Git index, no merge main or PR.
- OWNED: `verification/adversarial-20261028/**` only; registry and model untouched.
- Status: `ready_for_review` (initial record: `in_progress`).
- Initial ownership UTC: 2026-10-28T14:02:20.458333+00:00
- Next: review REPORT.md and apply only OWNED-path commits if accepted; new history runtime is a separate task.

Shared checkout `/Users/a/rwb_hak` is read-only for this task. Published SQL is read directly from Git objects. Heavy/full Olist runtime and dependency installs are prohibited by guard 78. A private tiny PG16 server is allowed by the task. New category-history runtime is outside this snapshot and requires a separately tasked recheck. Policy variants are observations, not automatically defects or approvals.

## Ready handoff

- Status: `ready_for_review`; verification complete for pinned snapshot.
- UTC update: 2026-10-28T14:17:18.216777+00:00.
- Initial ownership record above was written before source/test edits.
- Checkout branch observed before publication: `t3/verify-model-adversarially`, HEAD still `2f0a8de45aadc3b685f434aaaf736f0cca7c7f2e`. Publication uses only an isolated index and a separate ref; this checkout branch and common index are not advanced.
- Harness commit: `de3aab0a9e41b08502656e4c31a52a395237b4cd`; parent is exact input aab62d7.
- Publication branch: `t3/adversarial-20261028`, no main merge, no PR.
- Result: no confirmed new model defects. 1,678 baseline value comparisons; 5 metamorphic variants; 11/11 mutants killed; 6 invalid inputs rejected with committed model preserved; actual build/rebuild/answers/check and injected late-error rollback pass on 24 synthetic orders, PostgreSQL 16.15 / 16MB.
- Raw fixture content/DDL unchanged by build/rebuild. Own server stopped and private runtime removed. No dependencies installed; no heavy/full fixture or full Olist DB run.
- Eight local CSV hashes, headers and row counts match pinned input lock; this is not CSV/live-raw/core equality.
- Changed paths: only `verification/adversarial-20261028/**`. No edits to model, registry, other tests, app or another checkout.
- Report: [REPORT.md](REPORT.md). Machine findings: [findings.json](findings.json). Final execution: [results-ready/summary.json](results-ready/summary.json). Mutation exact edits/detectors are in that summary; no fabricated result substitution.
- Counterevidence: original fractional-timestamp rejection kept in `results-run01`; contract explicitly disallows fractional seconds. Intermediate successful runs retained in verified archives. Full logs retained with per-file hashes.
- Unchecked: full Olist DB lifecycle and final Q6–Q10 core answers, real CSV/raw equality, app, performance, newly implemented history and new address regression. Historical R1/R2/drop are not reopened.
- Next: integrator reviews report and may apply only this branch's OWNED-path commits. History runtime must receive a separate task against its published SHA. No human policy approvals are inferred or requested here.

Reproduce from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 verification/adversarial-20261028/run.py --output recheck-aab62d7
```
