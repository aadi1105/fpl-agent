# PHASE 3D — PREDICTION REALITY CHECK PROMPT

PROJECT RESET / CHECKPOINT — PREDICTION REALITY CHECK

STOP ALL FEATURE DEVELOPMENT AND OPTIMIZER DEVELOPMENT.

We have accumulated multiple modelling phases, audits, model versions,
diagnostic scripts and optimizer changes.

Before proceeding any further, we need to establish whether the actual
prediction engine is capable of making useful FPL predictions.

Do NOT:
- retrain models
- add new models
- modify the optimizer
- modify projection formulas
- add ownership adjustments
- add consensus adjustments
- hard-code players
- tune the system toward the current FPL template

==================================================
1. CREATE A SINGLE PROJECT STATE DOCUMENT
==================================================

Create:
docs/PROJECT_STATE.md

This must become the single source of truth for the current project.

Document:
A. PROJECT OBJECTIVE
B. CURRENT PRODUCTION MODELS
C. VALIDATED COMPONENTS
D. UNVALIDATED COMPONENTS
E. KNOWN ISSUES
F. CURRENT STOP CONDITION

==================================================
2. BUILD A HISTORICAL PREDICTION REALITY CHECK
==================================================

Create a new diagnostic module:
scripts/prediction_reality_check.py

This must evaluate the EXISTING production models without modifying them.
Use historical seasons/gameweeks for which both:
- pre-deadline information
- actual outcomes
are available.

CRITICAL:
Features must only use information available before that historical gameweek's deadline.
No future information.
No post-deadline statistics.
No future transfers.
No future minutes.
No future goals/xG/xA.
No leakage.

==================================================
3. RECONSTRUCT HISTORICAL PREDICTIONS
==================================================

For a large historical sample of player-gameweek observations, reconstruct:
Expected Minutes
P(start)
xG
xA
Clean Sheet Probability
DEFCON Probability
Expected FPL Points

using the SAME production models currently deployed.
Do not retrain anything.

==================================================
4. COMPARE PREDICTIONS TO REALITY
==================================================

For every component calculate:
Expected Minutes: MAE, RMSE, start probability calibration
xG: predicted xG vs actual goals, MAE, RMSE, calibration
xA: predicted xA vs actual assists, MAE, RMSE, calibration
Clean Sheet: predicted probability vs actual clean sheet, Brier score, calibration
Total FPL Points: predicted xP vs actual FPL points, MAE, RMSE, Pearson correlation, Spearman rank correlation

==================================================
5. BREAK DOWN RESULTS
==================================================

Evaluate performance by Position, Price tier, Historical minutes bucket, Recent form bucket, Transferred vs non-transferred players, Established vs low-sample players.

==================================================
6. CALIBRATION ANALYSIS
==================================================

For probability-based predictions (Expected Minutes / P(start), Clean Sheet, DEFCON where applicable), create calibration tables/plots.

==================================================
7. PLAYER-LEVEL SANITY CHECK
==================================================

Include established players (Haaland, Salah, Saka, Bruno Fernandes, Palmer, Isak, Watkins, Solanke, Wood, Gabriel, Raya) and previously identified problem cases (Awoniyi, Osula, Marmoush, Beto, João Pedro, Calvert-Lewin).

==================================================
8. CURRENT 2026/27 SNAPSHOT
==================================================

Separately display current production predictions for Haaland, Bruno Fernandes, Salah, Saka, Palmer, João Pedro, Calvert-Lewin, Gabriel, Awoniyi, Osula across GW1–GW4 & weighted 4-GW score.

==================================================
9. DO NOT USE FPL CONSENSUS AS GROUND TRUTH
10. DO NOT RUN THE OPTIMIZER
11. FINAL VERDICT (Answer 12 explicit questions with empirical metrics)
12. PROJECT ROADMAP UPDATE (Update docs/PROJECT_STATE.md, docs/ROADMAP.md, create docs/phases/PREDICTION_REALITY_CHECK.md)
==================================================
