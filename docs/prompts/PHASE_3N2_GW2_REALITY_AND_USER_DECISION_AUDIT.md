# PHASE 3N.2 — GW2 REALITY, PLAYER-ROLE & USER-DECISION AUDIT

OBJECTIVE:
Perform a comprehensive diagnostic, reality, and player-role audit to ensure the decision engine is 100% reliable for actual FPL decisions.

Key Requirements:
1. Absolute Current Gameweek & Data Freshness Audit (authoritative source vs DB, manager, projections, optimizer, API, frontend).
2. GW1 -> GW2 transition validation with historical immutability.
3. Complete 2026/27 player pool audit + diagnostic player cases (Haaland, Bruno, Havertz, Gyökeres, João Pedro, Calvert-Lewin, Marmoush, Awoniyi, Nelson, Ekitiké, Pope, Mateta).
4. Expected minutes audit & 75.0 minutes clustering investigation.
5. First-principles Gyökeres vs Havertz evaluation & selection mechanics explanation.
6. Transfer uncertainty general mechanism (`TRANSFER_UNCERTAIN`, `CLUB_CHANGE_PENDING`, `REGISTRATION_UNCERTAIN`).
7. Data quality classification (`GREEN`, `YELLOW`, `RED`) & Player Reality Flags (`EXPECTED_STARTER`, `ROTATION`, `BACKUP`, `INJURED`, etc.).
8. Interactive My Team Frontend Editor UI (ADD/REMOVE/CHANGE player, set bank, FT, chips, 15-player validation, search/filter, local/API persistence).
9. My Team vs Optimal Team visual panel & comparison engine (`MY TEAM NOT CONFIGURED` placeholder when empty).
10. Selection Trace Engine ("Why was this player selected?") & Non-Selection Trace Engine ("Why wasn't Player X selected?").
11. Diagnostic Top 20 rankings (GW2 xP, GW2-3, GW2-5, GW2-8).
12. Comprehensive automated regression test suite (`tests/test_phase3n2_reality_audit.py`).
13. Complete documentation updates (`docs/phases/PHASE_3N2_GW2_REALITY_AND_USER_DECISION_AUDIT.md`, `PROJECT_STATE.md`, `ROADMAP.md`, `DATA_PIPELINE.md`).
14. Final 28-point Acceptance Criteria Evaluation (`SAFE TO PROCEED TO GW2 DECISION OPTIMIZATION` or `NOT SAFE...`).
15. DO NOT MAKE FINAL GW2 SQUAD RECOMMENDATIONS OR EXECUTE TRANSFERS/CHIPS YET.
