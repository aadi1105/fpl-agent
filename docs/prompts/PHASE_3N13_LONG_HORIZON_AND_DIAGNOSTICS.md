# PHASE 3N.13 — LONG-HORIZON INTEGRITY + DIAGNOSTICS RENDERING AUDIT PROMPT

OBJECTIVE:
1. Audit and align Long Term mode horizon definitions across backend calculation (GW2–GW8, 7 Gameweeks, `[0.30, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05]`) and frontend display.
2. Update frontend metrics card headers and diagnostics panel titles to dynamically reflect selected mode (`1-GW Horizon xP`, `4-GW Weighted Horizon`, `7-GW Weighted Horizon`).
3. Make diagnostics endpoint (`GET /api/v1/projections/diagnostics`) mode-aware and start projections at target horizon (GW2).
4. Resolve Darlow expected minutes/projections discrepancy by executing `run_projections(start_gw=1, end_gw=8, force=True)`, ensuring zero-minute backup GKPs have 0.0 xMins and are not selected in starting XI.
5. Maintain 100% test coverage (80/80 passing) across 17 test suites without changing any underlying ML/optimizer models.
