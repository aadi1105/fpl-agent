# PHASE 3N.22 — FIX GAMEWEEK HISTORY USING THE CORRECT FPL MANAGER + CURRENT GAMEWEEK PROMPT

OBJECTIVE:
1. Diagnose and fix the root causes of wrong squad display and incorrect Gameweek status labeling in My Team Gameweek History.
2. Root Cause 1 Fix (Manager Entry ID Resolution & Fallback):
   - Prevent `effective_entry_id` from falling back to arbitrary stranger Entry ID `1` when `fpl_entry_id` is unconfigured/None.
   - For unlinked users, consume the user's canonical saved squad (`user_squads` / `user_picks`) with actual live/historical points.
   - For linked users, validate `requested_entry_id == configured_entry_id`. On mismatch, return explicit `MANAGER_MISMATCH` error structure so frontend displays `⚠️ FPL MANAGER DATA MISMATCH`.
3. Root Cause 2 Fix (Dynamic Current Gameweek Detection):
   - Determine Gameweek statuses dynamically:
     - Finished Gameweeks (`finished == True`, e.g. GW1) -> `COMPLETED`
     - Active Gameweek (first unfinished Gameweek, e.g. GW2) -> `🔴 LIVE`
     - Future Gameweeks (`gw > active_gw`, e.g. GW3+) -> `UPCOMING`
   - Preserve `CurrentGameStateManager.get_current_gameweek()` consistency with `database_is_current_gw` so existing reality audit test suites pass cleanly.
4. Cache Isolation:
   - Ensure cache keys are namespaced by manager `entry_id` and `gameweek` (`entry_picks_{entry_id}_gw_{gw}`).
5. Squad Protection:
   - Ensure browsing historical Gameweeks never mutates or overwrites the saved editable user squad.
6. Test Suite Expansion:
   - Create [`tests/test_phase3n22_manager_id_and_gameweek_fix.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n22_manager_id_and_gameweek_fix.py).
   - Ensure 120 / 120 tests pass across all 26 test suites.
