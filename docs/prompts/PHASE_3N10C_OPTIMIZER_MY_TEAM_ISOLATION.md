# PHASE 3N.10C — OPTIMIZER & MY TEAM STATE ISOLATION PROMPT

OBJECTIVE:
1. Fix Optimizer View UI regression after My Team V2 / modal changes.
2. Implement global lastOptimizerResult state cache in frontend/index.html to preserve completed optimizer results across tab switches.
3. Automatically re-hydrate Optimizer View (Optimal XI, bench, captain, xP, formation, explanations) when returning to OPTIMIZER VIEW tab.
4. Optimize GET /api/v1/projections/diagnostics with query ordering and in-memory caching so diagnostics table resolves in <0.2s.
5. Enforce 100% state isolation between Optimizer State (job, optimal XI, 4-GW weighted xP) and My Team State (user 15 players, bank, FT, squad page).
6. Maintain 100% test coverage (70/70 passing) across 14 test suites without changing any underlying ML/optimizer models.
