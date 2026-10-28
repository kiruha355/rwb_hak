.DEFAULT_GOAL := help

.PHONY: help build check control answers manifest rebuild-check dashboard

help:
	@printf '%s\n' 'build          atomic core + mart build from existing raw' 'check          rerun model/90_checks.sql in a transaction' 'control        pinned business controls (separate from build)' 'answers        execute numbered answers and named metric variants' 'manifest       verify the pinned eight CSV inputs' 'rebuild-check  build twice and compare model content fingerprints' 'dashboard      export core/mart to dashboard/data.js for dashboard/index.html' 'See docs/build-runbook.md for connection and raw reload protocol.'

build check control answers rebuild-check:
	@bash scripts/build-model.sh $@

manifest:
	@python3 scripts/input-manifest.py --data-dir data --verify-pinned

dashboard:
	@bash scripts/export-dashboard.sh
