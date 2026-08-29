# PHASE 3N.20 — MY TEAM PROJECTION INTEGRITY + MODEL AUDIT REPAIR + DEFAULT LANDING PAGE PROMPT

OBJECTIVE:
1. Fix root cause of 0.00 xP values on My Team pitch cards by resolving property-name key mismatches (`gw_xp`, `total_xp`, `expected_points_gw`, `gw0_xp`) in frontend card creation and backend pick dict serialization.
2. Fix root cause of invalid Model Audit data (0m xMins, 100% P(Start), 0.00 xP) by ensuring `get_diagnostics` handles Gameweek 2 horizon key lookups (`target_gw_key = target_gw if target_gw in horizon_gws else horizon_gws[0]`) cleanly when `target_gw` is passed.
3. Make My Team Command Center (`#tab-my-team`) the default active landing page displayed immediately upon visiting root URL `/`.
4. Ensure real expected-minutes probabilities ($P(\text{Start})$, $P(60+)$, $P(0)$) and expected minutes ($xMins$) decompose accurately for key players (Haaland: 76.2m, 84.9% start, 6.30 xP; Isak: 76.2m, 85.0% start, 6.58 xP; Joao Pedro: 68.2m, 77.1% start, 4.14 xP).
5. Create test suite `tests/test_phase3n20_projection_integrity_and_landing_page.py` (108/108 total tests passing cleanly across all 24 test suites).
