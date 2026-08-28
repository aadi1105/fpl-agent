# PHASE 3N.19 — PLAYER DATA EXPLORER + CURRENT GW LEADERS + MODEL AUDIT LOADING FIX PROMPT

OBJECTIVE:
1. Fix root cause of permanent "Loading..." state on Player Data and Model Audit pages.
2. Redesign Player Data page into a rich FPL Player Explorer with instant search (player name, full name, club), position filters (ALL, GKP, DEF, MID, FWD), and player cards displaying shirt SVGs, price, xP, xMins, and season points.
3. Add 🔥 CURRENT GAMEWEEK LEADERS section ranked exclusively by ACTUAL GW FPL points (event_points), clearly distinguished from xP/optimizer projections, with TOP 5 / TOP 10 toggle controls.
4. Implement unified Player Detail View providing:
   - Identity & Price
   - Upcoming 4-GW Fixture Run with Difficulty rating & projected xP (starting at current next GW, NO GW0!)
   - Production Model Metrics (xP, xMins, xG, xA, CS, DEFCON/CBIT)
   - Historical Actual FPL Points (GW1 actual score)
5. Add explicit loading, success, and retry error banners for API endpoints.
6. Create test suite `tests/test_phase3n19_player_explorer_and_audit.py` (105/105 total tests passing cleanly across all 23 test suites).
