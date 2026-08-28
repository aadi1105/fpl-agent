# PHASE 3N.1 — DECISION ENGINE REALITY AUDIT & CURRENT-STATE VALIDATION

OBJECTIVE:
Read-only diagnostic + targeted correction phase to verify current-state consistency across all layers (source -> state manager -> DB -> projection engine -> optimizer -> API -> frontend), audit fixtures, role/starter expected minutes integration, transfer uncertainty, persistent My Team configuration, decision explanations, fixture sensitivity, and mode horizon alignment.

Key Requirements:
1. Complete layer-by-layer gameweek consistency audit (`test_all_production_layers_use_same_current_gameweek()`).
2. GW2 fixture reconciliation across diagnostic players.
3. Expected minutes hard-input verification & role vs historical ability separation.
4. General transfer uncertainty mechanism (`TRANSFER_UNCERTAIN`, `CLUB_CHANGE_PENDING`, `REGISTRATION_UNCERTAIN`).
5. My Team configuration UI and API (15 player IDs, bank, free transfers, available chips).
6. Selection trace & decision explanation engine ("Why was this player selected?").
7. Fixture sensitivity audit (actual vs neutral fixture $\Delta xP$).
8. Haaland regression & full pool audit.
9. Comprehensive regression test suite (`tests/test_phase3n1_reality_audit.py`).
10. Final Safety Gate Verdict (`SAFE TO PROCEED TO GW2 DECISION OPTIMIZATION` or `NOT SAFE — DECISION ENGINE STILL HAS CRITICAL ISSUES`).
11. DO NOT MAKE FINAL GW2 SQUAD RECOMMENDATIONS OR EXECUTE TRANSFERS/CHIPS YET.
