FPL AI — PHASE 3A: EXPECTED GOALS (xG) ML MODEL

Phase 2C is complete.

The Expected Minutes ML system is now deployed in production as:

expected_minutes_v1

It has been trained on the corrected per-fixture historical dataset, validated out-of-sample, integrated into ProjectionEngine, and has a deterministic fallback.

Production coverage audit confirmed:

- 29,747 / 29,747 2025/26 test fixtures use expected_minutes_v1
- 590 / 590 active 2026/27 GW1 player projections use expected_minutes_v1
- 0% fallback usage in the audited sets
- All predictions are per-fixture and constrained to 0–90 minutes

We are now beginning the next prediction-model phase:

PHASE 3A — EXPECTED GOALS (xG)

IMPORTANT:

This phase is ONLY about predicting expected goals for an individual player in an individual fixture.

Do NOT train xA.

Do NOT train Clean Sheet.

Do NOT train DEFCON.

Do NOT train Bonus.

Do NOT modify the optimizer.

Do NOT modify squad selection.

Do NOT modify captaincy.

Do NOT change the 4-GW weighting.

Do NOT replace the production Expected Minutes model.

Do NOT build one giant FPL prediction model.

The objective is:

historical pre-deadline information
→ player-fixture xG prediction
→ out-of-sample validation
→ comparison against deterministic xG baseline
→ production integration ONLY if ML demonstrably improves the baseline.

==================================================
1. DEFINE THE PREDICTION TARGET
==================================================

The model must predict:

EXPECTED GOALS FOR ONE PLAYER IN ONE FIXTURE.

The fundamental prediction unit must be:

(season, gameweek, fixture_id, player_id)

NOT:

(player, gameweek)

This is critical because Double Gameweeks contain multiple fixtures.

Each fixture must receive its own xG prediction.

For example:

Player A — DGW GW30
    Fixture 1 → xG prediction
    Fixture 2 → xG prediction

GW30 total player xG:

xG_fixture_1 + xG_fixture_2

Do not aggregate DGW fixtures into a single training row.

==================================================
2. DEFINE THE TARGET PRECISELY
==================================================

Primary target:

target_goals

= actual goals scored by the player in that individual fixture.

The target must be:

0, 1, 2, ... etc.

Do NOT use total gameweek goals when a player has multiple fixtures.

Also investigate whether the existing data source provides reliable historical:

- xG
- shots
- shots on target
- big chances
- penalties
- touches in box

Use these as FEATURES only if they were available before the fixture deadline.

Do not accidentally use the target fixture's post-match statistics.

==================================================
3. CRITICAL TEMPORAL LEAKAGE RULE
==================================================

For a prediction for fixture F:

EVERY FEATURE must represent information available BEFORE the fixture deadline.

Forbidden:

- goals scored in target fixture
- xG in target fixture
- shots in target fixture
- assists in target fixture
- post-match BPS
- target-fixture minutes
- future gameweeks
- future team results
- final-season aggregates containing the target fixture
- future price values
- post-deadline injury/news information

Allowed examples:

- previous goals
- previous xG
- previous shots
- previous starts
- previous minutes
- previous xG/90
- previous goals/90
- previous shot volume
- previous team attacking strength
- previous opponent defensive strength
- upcoming opponent
- home/away
- historical player/team information available before the deadline

Build automated leakage tests.

==================================================
4. INSPECT THE AVAILABLE DATA FIRST
==================================================

Before writing the model:

Inspect the existing historical dataset and data sources.

Determine exactly which historical attacking features are actually available.

Do NOT assume xG data exists simply because the concept exists.

Report:

- available seasons
- available xG fields
- source of each field
- coverage by season
- missingness
- whether each field can be reconstructed pre-deadline

If reliable historical xG is available:

Use it.

If not:

Do NOT fabricate xG.

Use the strongest defensible historical attacking features available and clearly document the limitation.

==================================================
5. BUILD A LEAK-FREE xG DATASET
==================================================

Create a dedicated fixture-level historical xG dataset.

Use the same chronological philosophy as Phase 2A.

Prefer:

TRAIN:
2022/23 + 2023/24

VALIDATION:
2024/25

TEST:
2025/26

If data availability requires changing the split, document the exact reason.

Each row should represent:

PLAYER + FIXTURE + PRE-DEADLINE SNAPSHOT

Include appropriate features such as:

PLAYER:

- position
- price
- recent minutes
- recent starts
- recent goals
- recent xG
- recent xG/90
- recent shots
- recent shots on target
- recent big chances
- recent touches in box
- recent penalties if available

ROLLING WINDOWS:

- goals_last_1
- goals_last_3
- goals_last_5
- goals_last_10
- xG_last_1
- xG_last_3
- xG_last_5
- xG_last_10
- shots_last_3
- shots_last_5
- shots_last_10
- shots_on_target_last_5
- big_chances_last_5
- average_xG_per_90
- average_goals_per_90

Use only features that genuinely exist.

TEAM:

- team attack rating
- team defence rating
- opponent attack rating
- opponent defence rating
- home/away
- fixture difficulty

PLAYER AVAILABILITY:

- expected_minutes_v1
- p_start
- p_60_plus
- p_zero

IMPORTANT:

Use the PRODUCTION expected_minutes_v1 output.

Do NOT build another minutes model inside the xG model.

Minutes should enter the xG prediction as an explicit feature/context variable.

==================================================
6. BE VERY CAREFUL WITH MINUTES
==================================================

There are two conceptually different quantities:

1. Underlying attacking rate

Example:

xG per 90 = 0.55

2. Expected opportunity to play

Example:

expected minutes = 82

The model should learn the relationship between player attacking output and opportunity.

Do not accidentally train:

"player's historical goals per match"

without accounting for minutes.

The production expected_minutes_v1 prediction should be available as a pre-fixture feature.

Document exactly how it enters the xG model.

==================================================
7. DEFINE THE DETERMINISTIC BASELINE
==================================================

Before training ML, establish the current deterministic xG baseline.

Inspect the existing ProjectionEngine.

Document exactly how the current xG estimate is calculated.

The baseline must remain available.

Do NOT replace it.

The ML model must beat this baseline out-of-sample.

The comparison must be apples-to-apples:

Same player
Same fixture
Same historical information
Same target
Different prediction method

==================================================
8. CHOOSE THE RIGHT ML FORMULATION
==================================================

Do NOT automatically treat xG as ordinary regression without considering the target distribution.

Goals are count data.

The target contains many zeros and a smaller number of positive outcomes.

Evaluate appropriate formulations.

At minimum investigate:

A. Poisson regression baseline/model

B. Gradient-boosted regression approach such as LightGBM/XGBoost

If appropriate, also investigate:

- Tweedie regression
- Poisson objective in LightGBM/XGBoost

Do NOT blindly use a normal squared-error regression model if a count-aware formulation is more appropriate.

Document why the final approach was selected.

==================================================
9. EVALUATION METRICS
==================================================

Because goals are count outcomes, evaluate multiple metrics.

At minimum:

- MAE
- RMSE
- Poisson deviance / mean Poisson deviance
- calibration of aggregate expected goals

Where appropriate, also evaluate:

- rank correlation
- correlation between predicted and actual goals

Do NOT rely on a single metric.

Most importantly, compare:

DETERMINISTIC BASELINE
vs
ML MODEL

on the untouched 2025/26 test set.

==================================================
10. EVALUATE xG AS A RATE AND AS A TOTAL
==================================================

We need to distinguish:

A. Player attacking rate

from:

B. Expected goals for this fixture.

The final model output must represent:

EXPECTED GOALS IN THIS FIXTURE.

For example:

Haaland vs weak defence:
xG = 0.72

Haaland vs elite defence:
xG = 0.43

The model should respond sensibly to:

- player attacking ability
- expected minutes
- opponent defence
- team attack
- home/away
- recent attacking form where appropriate

==================================================
11. SANITY CHECKS
==================================================

Run controlled fixture comparisons.

Hold the player and other inputs constant and vary only the opponent.

Verify:

Weak opponent defence
→ higher predicted xG

Strong opponent defence
→ lower predicted xG

Also test:

Higher expected minutes
→ generally higher fixture xG, all else equal

Stronger team attack
→ generally higher player xG

Home advantage
→ sensible effect

Do not hard-code these relationships merely to make the tests pass.

They should emerge from the model/formula.

==================================================
12. PLAYER-LEVEL SANITY CHECKS
==================================================

Inspect representative players:

- premium striker
- premium midfielder
- regular starter
- low-minute forward
- attacking fullback
- cheap midfielder
- bench player

For each show:

Player
Opponent
Home/Away
Expected Minutes
Baseline xG
ML xG
Actual Goals

Do this for several fixtures across different difficulty levels.

==================================================
13. SUBGROUP PERFORMANCE
==================================================

Evaluate performance by:

POSITION:

- GKP
- DEF
- MID
- FWD

EXPECTED MINUTES:

- <30
- 30–60
- 60–75
- 75+

PLAYER HISTORICAL SAMPLE:

- low
- medium
- high

If a subgroup performs poorly, document it.

Do not automatically reject the entire model because of a small subgroup, but do not hide the result.

==================================================
14. TEMPORAL AND DGW VALIDATION
==================================================

Explicitly verify:

1. Every training row represents exactly one fixture.

2. target_goals <= reasonable fixture maximum.

3. No DGW row contains combined goals from multiple fixtures.

4. Rolling attacking features exclude the target fixture.

5. Future fixtures cannot influence historical features.

6. Historical team ratings use only information available before the fixture.

7. expected_minutes_v1 used as a feature comes from the appropriate pre-fixture prediction.

==================================================
15. MODEL SELECTION
==================================================

Use:

TRAIN:
2022/23 + 2023/24

VALIDATION:
2024/25

TEST:
2025/26

Use validation data to:

- choose model type
- choose hyperparameters
- choose features
- make modelling decisions

Do NOT use 2025/26 test performance to make modelling decisions.

Only evaluate the final selected model on the test set after the model is frozen.

==================================================
16. ERROR ANALYSIS
==================================================

Inspect:

- biggest positive errors
- biggest negative errors
- players with unexpected goals
- penalty takers
- low-minute players
- DGW fixtures
- rotation cases
- new players
- promoted teams

Remember:

A player scoring a goal does not mean the model was necessarily wrong.

xG is an expectation.

A 0.20 xG chance can result in a goal.

That is not automatically a prediction failure.

Distinguish:

MODEL ERROR

from:

NORMAL RANDOMNESS IN GOAL OUTCOMES.

==================================================
17. FEATURE IMPORTANCE
==================================================

For the selected ML model inspect feature importance.

Use appropriate methods such as:

- LightGBM feature importance
- permutation importance
- SHAP if already supported and practical

Pay particular attention to whether the model relies on sensible features:

- historical xG
- attacking rates
- minutes
- team attack
- opponent defence
- shots
- big chances

If suspicious features dominate, investigate.

Remember:

Feature importance is predictive importance, NOT causality.

==================================================
18. PRODUCTION DECISION
==================================================

Do NOT automatically deploy the xG ML model.

Deploy ONLY if:

- no temporal leakage
- correct per-fixture target
- DGW handling is correct
- ML materially improves out-of-sample performance
- model behaves sensibly
- no catastrophic subgroup failures
- production inference is reliable
- expected_minutes_v1 integration is correct
- deterministic fallback exists

If ML does NOT convincingly beat the baseline:

KEEP THE DETERMINISTIC xG MODEL.

Document the result.

Do not force ML into production.

==================================================
19. PRODUCTION INTERFACE IF APPROVED
==================================================

If deployment is approved, create a clean xG prediction interface.

For example:

xg_predictor.py

Output:

player_id
fixture_id
gameweek
xg_ml
model_version
used_fallback

The output must represent:

EXPECTED GOALS FOR THAT SINGLE FIXTURE.

For DGWs:

Fixture 1 xG
+
Fixture 2 xG
=
GW total xG

Do not aggregate fixtures inside the predictor itself.

==================================================
20. FALLBACK
==================================================

If the ML xG model:

- cannot load
- lacks required features
- produces invalid output
- inference fails

fall back to the deterministic xG baseline.

Return:

used_fallback=True

and:

model_version="xg_baseline_v1"

Do not silently return zero.

Log fallback events.

==================================================
21. PROJECTION ENGINE INTEGRATION
==================================================

If approved for production:

Current architecture becomes:

expected_minutes_v1
        +
team/fixture context
        +
xG ML
        ↓
FPL scoring engine
        ↓
xP

Do NOT modify xA, Clean Sheet, DEFCON or Bonus yet.

Those remain their existing deterministic/statistical implementations.

Ensure expected minutes is not double-counted.

There must be one authoritative expected-minutes input.

==================================================
22. DIAGNOSTICS
==================================================

Extend projection diagnostics to expose:

Player
Gameweek
Fixture
Opponent
Home/Away

Expected Minutes
P(start)

Baseline xG
ML xG
xG model version
Fallback status

Then downstream:

Goals points
Assists
Clean Sheet
DEFCON
Bonus
Total xP

This allows us to see exactly how xG changes the final projection.

==================================================
23. CURRENT 2026/27 FORWARD PREDICTIONS
==================================================

After model selection, it is acceptable to run the final model against the current 2026/27 fixture data for forward-looking predictions.

BUT:

These are predictions, NOT evaluation results.

Do NOT use future 2026/27 outcomes for training.

Do NOT claim the model has been validated on 2026/27.

Show a few examples of current GW1 predictions.

==================================================
24. MODEL VERSIONING
==================================================

If deployed, register:

xg_v1

and preserve:

xg_baseline_v1

Record:

- model type
- target definition
- training seasons
- validation season
- test season
- features
- hyperparameters
- metrics
- artifact location
- deployment date

Do not overwrite the baseline.

==================================================
25. TESTS
==================================================

Add tests covering:

- target construction
- per-fixture representation
- DGW handling
- temporal feature construction
- leakage prevention
- model loading
- inference
- output schema
- non-negative xG
- sensible upper bounds
- fallback behavior
- expected_minutes_v1 integration
- no double-counting
- diagnostics
- production projection integration if deployed

Run:

python -m pytest

All previous tests must continue to pass.

==================================================
26. DOCUMENTATION — MANDATORY
==================================================

Update the project documentation as part of this phase.

THIS IS NOW A PERMANENT RULE:

EVERY FUTURE DEVELOPMENT PHASE MUST UPDATE THE PROJECT DOCUMENTATION.

Update:

docs/ROADMAP.md

docs/phases/PHASE_3A_EXPECTED_GOALS.md

docs/models/MODEL_REGISTRY.md

docs/models/ML_MODELS.md

docs/data/DATA_DICTIONARY.md

docs/data/DATA_PIPELINE.md if the dataset pipeline changes

docs/decisions/ARCHITECTURAL_DECISIONS.md if a new architectural decision is made

docs/README.md if necessary

Save this exact development prompt as:

docs/prompts/PHASE_3A_EXPECTED_GOALS.md

Clearly distinguish:

- IMPLEMENTED
- TRAINED
- EVALUATED
- APPROVED
- DEPLOYED
- FALLBACK
- PLANNED

Do not describe xG ML as deployed unless the deployment decision is explicitly positive.

==================================================
27. FINAL REPORT
==================================================

Return a complete report containing:

1. Data sources inspected
2. Dataset size
3. Target definition
4. Feature list
5. Baseline methodology
6. ML approaches tested
7. Train/validation/test split
8. Leakage audit
9. DGW audit
10. Test-set metrics
11. Baseline vs ML comparison
12. Subgroup performance
13. Sanity checks
14. Error analysis
15. Feature importance
16. Production decision
17. Integration details if deployed
18. Fallback details
19. Model version
20. Tests
21. Documentation updates

Do not hide negative results.

If ML fails to beat the baseline, explicitly say:

"ML xG model NOT DEPLOYED — deterministic baseline retained."

==================================================
STOP CONDITION
==================================================

STOP AFTER PHASE 3A.

Do NOT begin xA.

Do NOT begin Clean Sheet.

Do NOT begin DEFCON.

Do NOT begin Bonus.

Do NOT modify the optimizer.

Wait for review of the Phase 3A results before proceeding.
