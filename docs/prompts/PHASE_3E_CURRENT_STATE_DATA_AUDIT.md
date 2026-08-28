# PHASE 3E — 2026/27 CURRENT-STATE PLAYER, TRANSFER & FIXTURE AUDIT

STOP MODEL DEVELOPMENT AND STOP OPTIMIZER DEVELOPMENT.

We have completed the Prediction Reality Check and established that the
historical production models contain useful predictive signal.

However, the current 2026/27 production snapshot contains a critical
data-integrity problem:

Taiwo Awoniyi is still represented as a Nottingham Forest player with a
Forest fixture, despite having transferred to Coventry City.

This proves that our current-season player/team/fixture state cannot yet be
trusted.

This phase is ONLY about establishing a correct current representation of
the 2026/27 FPL world.

DO NOT:
- retrain ML models
- modify xG/xA models
- modify minutes models
- modify clean-sheet models
- modify DEFCON
- modify the optimizer
- modify xP formulas
- add ownership adjustments
- manually blacklist players
- manually boost players

==================================================
1. CANONICAL CURRENT DATA SOURCE
==================================================

Determine the authoritative current 2026/27 FPL data source.
Use the official FPL API/bootstrap data as the canonical source for:
- player ID
- web_name
- first name
- second name
- team ID
- element type
- now_cost
- status
- chance_of_playing
- news
- selected_by_percent
- current FPL team

Use the current FPL fixture feed as the canonical source for:
- fixture ID
- gameweek
- team_h
- team_a
- difficulty
- kickoff

==================================================
2. AUDIT ALL 2026/27 PLAYERS
3. TRANSFER AUDIT (Create docs/data/TRANSFERS_2026_27.csv)
4. AWONIYI TEST CASE (Verify Awoniyi -> Coventry City)
5. FIXTURE CONSISTENCY (Hard validation check)
6. CURRENT-CLUB VALIDATION
7. HISTORICAL DATA VS CURRENT STATE
8. PLAYER AVAILABILITY
9. PRICE INTEGRITY
10. CURRENT FIXTURE SNAPSHOT
11. CRITICAL PLAYER SANITY CHECK
12. FRONTEND CONSISTENCY & TIMESTAMP
13. TESTS (Regression tests for team/fixture validation)
14. REGENERATED GW1-GW4 PROJECTIONS
15. RANKED GW1 TABLE BEFORE OPTIMIZATION
16. DOCUMENTATION & STOP CONDITION
==================================================
