FPL AI — PHASE 3C
CLEAN SHEET & DEFCON ML MODELS

We are now beginning Phase 3C.

Previous phases completed:

- Fixture-aware projections
- Team strength ratings
- DGW per-fixture representation
- Expected Minutes ML model
- Expected Minutes role/transfer calibration
- Current 2026/27 player-price integrity audit
- Optimizer mode routing
- Real optimization progress tracking
- Position-aware price/value diagnostics

The current system now has:

Minutes: expected_minutes_v1 (ML DEPLOYED)
xG: existing xG model (ML DEPLOYED)
xA: existing xA model (ML DEPLOYED)

Clean Sheet / DEFCON / Bonus remain statistical baselines.

The goal of Phase 3C is to build and evaluate ML models for:

1. Clean Sheet probability
2. Defensive Contribution / DEFCON probability

Do NOT modify the optimizer.

Do NOT modify the expected-minutes model.

Do NOT retrain xG or xA.

Do NOT build a single giant FPL prediction model.

==================================================
0. 2026/27 FPL RULES — SOURCE OF TRUTH
==================================================

Use the official 2026/27 FPL rules and the project's existing scoring engine.

IMPORTANT:

Defensive Contribution remains in 2026/27.

For defenders:
10 combined CBIT in a single match → +2 FPL points.

CBIT =
- Clearances
- Blocks
- Interceptions
- Tackles

For midfielders and forwards:
12 combined defensive contributions are required.

Their defensive contribution total includes:
- Clearances
- Blocks
- Interceptions
- Tackles
- Recoveries

The +2 points are capped at one award per match.

Do NOT assume:
10 CBIT → 4 points
20 CBIT → 4 points

The threshold gives a single +2-point award.

Also account for the 2026/27 BPS changes separately from DEFCON.

Do NOT reuse an old BPS model without verifying compatibility with the 2026/27 scoring rules.

Document the exact scoring assumptions.

==================================================
1. AUDIT THE EXISTING STATISTICAL BASELINES
==================================================

Before building anything, inspect the current:

- Clean Sheet probability model
- DEFCON probability model
- Bonus model
- Defensive action features
- Team defensive strength features
- Opponent attacking strength features
- Player CBIT rates
- Player recovery rates
- Fixture difficulty features

Document:

- inputs
- formulas
- assumptions
- fallback logic
- data sources
- known weaknesses

Do NOT replace anything until the baseline is understood.

==================================================
2. BUILD A LEAK-FREE HISTORICAL CLEAN SHEET DATASET
==================================================

Create a historical per-fixture dataset.

One row must represent:

(season, gameweek, fixture_id, team_id)

This is a TEAM-FIXTURE clean-sheet prediction problem.

Target:

clean_sheet = 1 if team conceded 0 goals
clean_sheet = 0 otherwise

Features must contain ONLY information available before the fixture.

==================================================
3. TRAIN CLEAN SHEET MODELS
==================================================

Build at least:

Baseline:
existing deterministic/statistical clean-sheet model.

ML candidate:
a suitable probabilistic classifier such as LightGBM/XGBoost/logistic regression depending on dataset size and existing infrastructure.

The model should output:

P(clean sheet)

Evaluate using strict chronological out-of-sample testing.

Use:

- LogLoss
- Brier score
- calibration
- ROC-AUC as secondary metric
- MAE if useful

==================================================
4. CLEAN SHEET HOME/AWAY CALIBRATION
==================================================

Explicitly evaluate:

- home fixtures
- away fixtures
- strong defenses
- weak defenses
- strong opponents
- weak opponents
- promoted teams
- low-sample teams

==================================================
5. BUILD A LEAK-FREE DEFCON DATASET
==================================================

Create a historical per-player-fixture dataset.

One row:

(season, gameweek, fixture_id, player_id)

Target:

DEFCON = 1
if player reached the FPL defensive-contribution threshold in that match.

DEFCON = 0 otherwise.

For defenders:

CBIT >= 10

For midfielders/forwards:

CBIRT >= 12

==================================================
6. DEFCON FEATURES
==================================================

Construct only pre-fixture features.

==================================================
7. DEFCON MODEL
==================================================

Compare:

Existing Poisson DEFCON model
vs
ML probability model.

==================================================
8. POSITION-SPECIFIC DEFCON
==================================================

DEF: threshold = 10 CBIT
MID/FWD: threshold = 12 CBIRT

==================================================
9. DOUBLE GAMEWEEK HANDLING
==================================================

GW DEFCON expected points = sum of fixture-level expected DEFCON points.

==================================================
10. LOW-SAMPLE / TRANSFER HANDLING
==================================================

Use current-club evidence where available.

==================================================
11. INTEGRATE EXPECTED MINUTES
==================================================

Use the deployed expected_minutes_v1 model as an input.

==================================================
12. FPL SCORING ENGINE
==================================================

Keep the scoring engine deterministic.

==================================================
13. 2026/27 BPS
==================================================

Audit the existing Bonus model against the official 2026/27 BPS changes.

==================================================
14. DEPLOYMENT CRITERIA
==================================================

Deploy ML only if it outperforms the baseline on out-of-sample evidence.

==================================================
15. FINAL PROJECTION OUTPUT
==================================================

Generate GW-specific projections.

==================================================
16. BACKTEST THE COMPLETE PIPELINE
==================================================

Run a chronological end-to-end backtest.

==================================================
17. FRONTEND
==================================================

Update diagnostics and detail modals.

==================================================
18. TESTS
==================================================

Add regression tests.

==================================================
19. DOCUMENTATION
==================================================

Update project documentation.

==================================================
20. STOP CONDITION
==================================================

STOP and wait for review.
