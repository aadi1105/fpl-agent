# PHASE 3N.6 — MY TEAM LOADING UX + SQLITE CONCURRENCY / OPTIMIZER FAILURE PROMPT

OBJECTIVE:
1. Fix delayed player picker in Edit My Team by switching to fast canonical GET /api/v1/players endpoint (0.11s vs 51.29s).
2. Fix SQLite (sqlite3.OperationalError) database is locked failure via WAL mode, 30s busy timeout, and bulk single-commit projection batching.
3. Add visible loading, error, and retry states for player picker and optimizer job failure.
4. Maintain 100% test coverage (47/47 passing) across all 9 test suites.
