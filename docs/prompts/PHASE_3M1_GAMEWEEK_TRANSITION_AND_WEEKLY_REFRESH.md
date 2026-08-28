# PHASE 3M.1 — GAMEWEEK TRANSITION, WEEKLY REFRESH & OPTIMIZER UX FOUNDATION

OBJECTIVE:
Fix and verify temporal gameweek transition (GW1 -> GW2 -> GW3), build weekly refresh pipeline orchestrator, establish persistent "My Team" architecture, implement genuine multi-horizon optimization modes (GW2, GW2-GW3, GW2-GW5, GW2-GW8), and construct My Team vs Optimal Team comparison UI.

Key Requirements:
1. Authoritative Gameweek Transition (GW1 -> GW2 transition with frozen GW1 snapshot `2026_27_GW1_STATE_v1` and active GW2 snapshot `2026_27_GW2_STATE_v1`).
2. Historical Immutability (GW1 actuals persisted without overwriting historical records).
3. `refresh_current_gameweek()` orchestrated pipeline with state tracking (READY, SYNCING, FAILED, etc.).
4. Persistent "My Team" User Squad State (storing 15 player IDs, bank, free transfers, available chips).
5. Real Horizon Optimization Modes:
   - Mode 1: NEXT GAMEWEEK (GW2 only)
   - Mode 2: SHORT TERM (GW2–GW3)
   - Mode 3: MEDIUM TERM (GW2–GW5)
   - Mode 4: LONG TERM (GW2–GW8)
6. Frontend 3-Panel / Dual View: MY TEAM vs OPTIMAL TEAM with difference highlighting (KEEP, SELL, BUY).
7. Comprehensive automated regression test suite (`tests/test_phase3m1_transition.py`).
8. Safety Gate Verdict: `SAFE TO PROCEED TO GW2 DECISION OPTIMIZATION`.
9. DO NOT MAKE FINAL GW2 SQUAD RECOMMENDATION OR EXECUTE TRANSFERS YET.
