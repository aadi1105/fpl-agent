# PHASE 3N.23 — IMMUTABLE GAMEWEEK TEAM HISTORY + BENCH POINTS + SEASON HISTORY + CHIPS PROMPT

OBJECTIVE:
1. Fix Bench Player Points Calculation:
   - Resolve raw actual points for all 15 players (starters and bench).
   - Eliminate multiplying bench player points by 0 on player cards (`createPlayerCard(p)` in `frontend/index.html`).
   - Display raw actual points scored by bench players (e.g. M.Sangaré 14 pts, Thomas 3 pts, van Ewijk 1 pt, Kinsky 3 pts -> 21 bench pts total).
   - Distinguish `ACTUAL POINTS` vs `PROJECTED xP`. If actual points are unavailable (future GW), display `— pts`.
2. Introduce Dedicated Immutable Historical Snapshot Model (`GameweekTeamSnapshot`):
   - Create model in `backend/models.py` storing frozen completed Gameweek snapshots (`picks_json`, `starting_xi_ids`, `bench_ids`, `captain_id`, `vice_captain_id`, `active_chip`, `starting_xi_points`, `captain_bonus`, `bench_points`, `net_gw_score`, `overall_points`, `overall_rank`, `is_final`).
   - Freeze completed Gameweek snapshots once marked `finished`.
   - Ensure browsing or mutating Current Squad (`user_squads` / `user_picks`) NEVER alters or overwrites historical snapshots (e.g. GW1).
3. Build Season History & Chips API:
   - Add `get_season_history()` method in `FPLHistoryService` ([`backend/services/fpl_history_service.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/services/fpl_history_service.py)).
   - Register endpoint `GET /api/v1/user-squad/season-history` returning:
     - 38 Gameweek History rows (`gw`, `status`, `net_gw_score`, `captain_name`, `bench_points`, `transfers_count`, `points_cost`, `active_chip`, `overall_points`, `overall_rank`, `team_value_str`)
     - Season Summary Metrics (`total_points`, `gw_avg`, `best_gw`, `worst_gw`, `current_rank`, `total_transfers`, `chips_used_count`)
     - Chip Status list for all 4 FPL chips (`Wildcard`, `Free Hit`, `Bench Boost`, `Triple Captain`) with status `USED — GWX` or `AVAILABLE`.
4. Frontend UI Enhancements:
   - Add dedicated **CHIP STATUS & AVAILABILITY** panel on `#tab-my-team`.
   - Add compact **SEASON SUMMARY** metrics bar.
   - Add interactive **SEASON GAMEWEEK HISTORY & PERFORMANCE** table with clickable rows.
5. Create Test Suite:
   - Create [`tests/test_phase3n23_immutable_snapshots_and_season_history.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n23_immutable_snapshots_and_season_history.py).
   - Verify all 126 tests pass 100% across all 27 test suites.
