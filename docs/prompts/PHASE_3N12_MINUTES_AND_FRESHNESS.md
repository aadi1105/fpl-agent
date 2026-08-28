# PHASE 3N.12 — EXPECTED-MINUTES COMPETITION + LIVE DATA FRESHNESS AUDIT PROMPT

OBJECTIVE:
1. Audit expected minutes pipeline and implement club-level role competition reconciliation layer (`reconcile_squad_minutes`) for mutually exclusive starting roles (e.g. Goalkeepers).
2. Trace last sync timestamp source (`2026-08-20`) and fix frontend banner rendering so `data-synced-banner` dynamically reflects backend snapshot `generated_at` timestamp.
3. Validate role competition with before/after examples and confirm optimizer consumes reconciled expected minutes.
4. Maintain 100% test coverage (76/76 passing) across 16 test suites without changing any underlying ML/optimizer models.
