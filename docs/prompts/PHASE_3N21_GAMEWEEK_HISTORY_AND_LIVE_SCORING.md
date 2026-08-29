# PHASE 3N.21 — MY TEAM GAMEWEEK HISTORY + LIVE FPL SCORING PROMPT

OBJECTIVE:
1. Extend My Team Command Center with a prominent Gameweek Selector (`[ ← ] GW1 [ → ]` & dropdown `[ GW1 🔴 LIVE ]`) and horizontal Gameweek History Strip.
2. Build backend service `FPLHistoryService` in `backend/services/fpl_history_service.py` consuming official FPL endpoints:
   - `GET /api/entry/{entry_id}/event/{gw}/picks/` for historicalSubmitted picks & chips
   - `GET /api/event/{gw}/live/` for live player statistics (`total_points`, `minutes`, `goals_scored`, `assists`, `clean_sheets`, `saves`, `bonus`)
3. Calculate Gameweek Scoreboard metrics:
   - `starting_xi_points`: Starting XI total points
   - `captain_bonus`: Captain extra points (2x for standard C, 3x for Triple Captain)
   - `bench_points`: Total bench points
   - `transfers_count` & `points_cost`: Transfers made & points hits (-4, etc.)
   - `net_gw_score`: Net Gameweek total
   - `overall_points`, `overall_rank`, `gw_rank`, `active_chip`
4. Incorporate automatic substitutions (`automatic_subs`) and Vice-Captain takeover if Captain played 0 minutes (`minutes == 0`).
5. Render player cards on historical pitch displaying **ACTUAL POINTS** (`8 pts`) AND **PROJECTED XP** (`5.62 xP`) side-by-side with clear labels.
6. Support Future Gameweeks (e.g. GW3+) showing projected upcoming squad with projected $xP$ and **NO fabricated actual points** (`pts: —`).
7. Implement 60-second lightweight auto-polling during live active Gameweeks.
8. Enforce Architectural Protection: Browsing historical Gameweeks updates pitch view without altering or overwriting the user's saved editable squad (`user_squads` DB table).
9. Add explicit error states (`⚠️ GAMEWEEK DATA UNAVAILABLE [ 🔄 RETRY LOADING ]`) to prevent fake 0s on network/API failure.
10. Create test suite `tests/test_phase3n21_gameweek_history_and_live_scoring.py` (113/113 total tests passing cleanly across all 25 test suites).
