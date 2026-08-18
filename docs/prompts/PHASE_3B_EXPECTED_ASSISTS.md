FPL AI — PHASE 3B: EXPECTED ASSISTS (xA) ML MODEL

Phase 3A is complete.

The Expected Goals ML system is now deployed in production as:

xg_v1_lgbm

Phase 3A established:

- Fixture-level prediction unit
- Leak-free historical dataset
- Chronological train/validation/test split
- Poisson LightGBM xG model
- Out-of-sample improvement over deterministic xG baseline
- Production integration with expected_minutes_v1
- Deterministic fallback
- DGW per-fixture handling
- Diagnostics
- Model versioning
- Documentation

The xG model remains deployed.

We are now beginning:

PHASE 3B — EXPECTED ASSISTS (xA) ML MODEL

IMPORTANT:

This phase is ONLY about predicting expected assists for an individual player in an individual fixture.

Do NOT train Clean Sheet.

Do NOT train DEFCON.

Do NOT train Bonus.

Do NOT modify the optimizer.

Do NOT modify squad selection.

Do NOT modify captaincy.

Do NOT change the 4-GW weighting.

Do NOT replace expected_minutes_v1.

Do NOT modify xg_v1_lgbm.

Do NOT build one giant FPL prediction model.

The objective is:

historical pre-deadline information
→ player-fixture xA prediction
→ out-of-sample validation
→ comparison against deterministic xA baseline
→ production integration ONLY if ML demonstrably improves the baseline.

==================================================
1. DEFINE THE PREDICTION UNIT
==================================================

The fundamental prediction unit MUST be:

(season, gameweek, fixture_id, player_id)

Exactly one player in exactly one fixture.

Do NOT use:

(player, gameweek)

as the modelling unit.

Double Gameweeks must contain separate observations.

Example:

Player A — GW30

Fixture 1 → xA prediction
Fixture 2 → xA prediction

GW30 total xA:

xA_fixture_1 + xA_fixture_2

Do not aggregate the two fixtures into one training target.

==================================================
2. DEFINE THE TARGET
==================================================

Primary target:

target_assists

= actual FPL assists credited to the player in that individual fixture.

The target must represent the actual number of assists in THAT fixture only.

Do not use:

- gameweek-total assists
- season-total assists
- future assists
- target-fixture expected assists
- post-match chance creation statistics

if those are not available before the deadline.

Investigate exactly how assists are represented in the historical source.

Document:

- source
- definition
- edge cases
- missing values
- whether own goals/deflections/penalty situations affect the target
- whether the historical assist definition matches FPL scoring

Do not silently change the target definition.

==================================================
3. FIRST INSPECT THE AVAILABLE DATA
==================================================

Before implementing the model, inspect the existing data pipeline.

Determine which historical attacking/creative features are actually available.

Potential features include:

PLAYER:

- recent assists
- recent xA
- recent chances created
- recent key passes
- recent crosses
- recent big chances created
- recent touches in opposition box
- recent passes in final third
- recent progressive passes if available
- recent set-piece involvement if available
- recent minutes
- position
- price

ROLLING WINDOWS:

- assists_last_1
- assists_last_3
- assists_last_5
- assists_last_10
- xA_last_1
- xA_last_3
- xA_last_5
- xA_last_10
- chances_created_last_3
- chances_created_last_5
- chances_created_last_10
- key_passes_last_5
- big_chances_created_last_5
- xA_per_90

Only use features that actually exist and can be constructed without leakage.

Do NOT invent historical xA/chance-creation data.

If a proposed feature is unavailable, document that fact and continue with the strongest defensible feature set.

==================================================
4. TEMPORAL LEAKAGE — NON-NEGOTIABLE
==================================================

For a prediction for fixture F:

EVERY FEATURE must represent information available strictly BEFORE fixture F.

Forbidden:

- assists in target fixture
- xA in target fixture
- chances created in target fixture
- key passes in target fixture
- target fixture minutes
- target fixture BPS
- future fixtures
- future team results
- final-season aggregates containing target fixture
- post-deadline injury/news information

Allowed:

- historical assists
- historical xA
- historical chance creation
- historical minutes
- historical creative rates
- historical team attacking strength
- historical opponent defensive strength
- upcoming fixture information
- home/away
- expected_minutes_v1
- expected_minutes_v1 availability probabilities

Build automated leakage tests.

==================================================
5. HISTORICAL DATASET
==================================================

Create a dedicated fixture-level historical xA dataset.

Use the same chronological philosophy as previous models:

TRAIN:
2022/23 + 2023/24

VALIDATION:
2024/25

TEST:
2025/26

If data availability requires a different split, document why.

The final dataset should contain one row per:

season
gameweek
fixture_id
player_id

Verify:

- no duplicate player-fixture rows
- no aggregated DGW rows
- target_assists refers to exactly one fixture
- no target-fixture statistics leak into features

==================================================
6. IMPORTANT: xA IS NOT THE SAME AS ASSISTS
==================================================

Treat this distinction explicitly.

ASSISTS are discrete outcomes.

xA represents the expected value/quality of assist opportunities.

A player can have:

0.80 xA
and
0 assists

without the model necessarily being wrong.

Conversely:

0.10 xA
and
1 assist

can happen due to normal randomness.

The objective is NOT to predict assists perfectly.

The objective is to estimate the player's expected assist contribution.

Document this distinction.

==================================================
7. USE PRODUCTION EXPECTED MINUTES
==================================================

The xA model must use the existing production:

expected_minutes_v1

and, where useful:

p_start
p_60_plus
p_zero

Do NOT build another hidden minutes model.

Do NOT independently estimate minutes.

Expected minutes should be treated as pre-fixture availability/opportunity information.

Document exactly how expected_minutes_v1 enters the xA model.

==================================================
8. USE THE PRODUCTION xG MODEL ONLY WHERE JUSTIFIED
==================================================

Investigate whether:

xg_v1_lgbm

should be used as an input feature for xA.

Do NOT automatically include it.

Ask:

Does expected goals create useful information about assist opportunities?

Could it create unwanted coupling between the two models?

Could it cause circularity or double-counting?

If xG is used:

- use only the pre-fixture xg_v1_lgbm prediction
- never use target-fixture xG
- document the reason
- test whether it actually improves validation performance

If xG does not help, leave it out.

Do not add dependencies simply because the model already exists.

==================================================
9. DEFINE THE DETERMINISTIC xA BASELINE
==================================================

Inspect the existing projection engine.

Determine exactly how deterministic xA is currently calculated.

Preserve it as:

xA_baseline_v1

The baseline must remain available for comparison.

Do not replace it before evaluation.

The ML model must beat the baseline out-of-sample to be considered for deployment.

==================================================
10. MODEL FORMULATION
==================================================

Assists are count outcomes with many zeros.

Do not automatically use ordinary L2 regression.

Evaluate appropriate approaches.

At minimum investigate:

A. Poisson regression / Poisson LightGBM

B. LightGBM/XGBoost regression using an appropriate count-oriented objective

If appropriate, investigate:

- Tweedie
- zero-inflated approaches
- other count-aware formulations

Do not over-engineer.

Start with simple, defensible models.

Use the 2024/25 validation season to select the formulation.

==================================================
11. VALIDATION METRICS
==================================================

Evaluate multiple metrics.

At minimum:

- Mean Poisson Deviance
- MAE
- RMSE

Also report:

- Spearman rank correlation
- Pearson correlation
- aggregate calibration ratio

Where practical, include bucket calibration:

Predicted xA bucket
vs
Actual assists per fixture

Do NOT rely on a single metric.

The key comparison is:

xA_baseline_v1
vs
ML xA model

on the frozen 2025/26 test set.

==================================================
12. MODEL SELECTION
==================================================

Use:

TRAIN:
2022/23 + 2023/24

VALIDATION:
2024/25

TEST:
2025/26

Use validation only for:

- formulation selection
- feature selection
- hyperparameters
- modelling decisions

Do NOT tune against 2025/26.

The test set must remain frozen until the final model is selected.

==================================================
13. CALIBRATION
==================================================

Evaluate whether predicted xA corresponds sensibly to actual assists.

Produce predicted-xA buckets.

For each bucket report:

- number of fixtures
- mean predicted xA
- actual assists per fixture
- predicted/actual ratio

Pay particular attention to:

- very low xA
- regular creative players
- premium creative players
- high-xA players

Do not assume aggregate calibration is sufficient.

==================================================
14. SANITY CHECKS
==================================================

Run controlled fixture comparisons.

Holding the player and other variables constant:

WEAKER OPPONENT DEFENCE
→ should generally allow greater xA opportunity.

STRONGER TEAM ATTACK
→ should generally increase xA opportunity.

HIGHER EXPECTED MINUTES
→ should generally increase fixture xA.

HOME/AWAY
→ should produce a sensible effect where supported by the data.

Do NOT hard-code relationships solely to make tests pass.

==================================================
15. PLAYER-LEVEL SANITY CHECKS
==================================================

Inspect representative players:

- premium creator
- premium goal-scoring midfielder
- creative midfielder
- attacking fullback
- low-minute attacker
- low-price midfielder
- bench player

For each show:

Player
Opponent
Home/Away
Expected Minutes
Baseline xA
ML xA
Actual Assists

Inspect whether predictions behave sensibly.

==================================================
16. SUBGROUP PERFORMANCE
==================================================

Evaluate test performance by:

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

HISTORICAL CREATIVE SAMPLE:

- low
- medium
- high

Document weaknesses.

Do not hide poor subgroup performance.

Do not automatically reject the entire model because of a tiny subgroup.

==================================================
17. ERROR ANALYSIS
==================================================

Inspect representative cases where:

- predicted xA was high but actual assists = 0
- predicted xA was low but actual assists > 0
- player created many chances but received no assists
- player recorded an unexpected assist
- player had very low minutes
- player returned from injury
- player had unusual fixture circumstances

Remember:

xA is an expectation.

A high xA with zero assists is NOT automatically a model failure.

A low xA with one assist is NOT automatically a model failure.

Distinguish:

PREDICTION ERROR

from

NORMAL OUTCOME VARIANCE.

==================================================
18. FEATURE IMPORTANCE
==================================================

Inspect feature importance for the selected ML model.

Use:

- LightGBM feature importance
- permutation importance
- SHAP if already supported and practical

Pay attention to whether sensible creative features dominate:

- historical xA
- chances created
- key passes
- creative rate
- expected minutes
- team attack
- opponent defence

If suspicious features dominate, investigate.

Remember:

Feature importance is predictive importance, not causality.

==================================================
19. TEST FOR XG DEPENDENCY
==================================================

If xg_v1_lgbm is considered as a feature:

Run an ablation comparison:

MODEL A:
xA model WITHOUT xG prediction

MODEL B:
xA model WITH xg_v1_lgbm prediction

Compare validation performance.

Only keep xG as a feature if it provides meaningful improvement without creating undesirable coupling or leakage.

Document the result.

==================================================
20. PRODUCTION DECISION
==================================================

Do NOT automatically deploy the ML xA model.

Deploy ONLY if:

- no temporal leakage
- correct per-fixture target
- DGW handling is correct
- test-set performance materially improves over baseline
- predictions behave sensibly
- calibration is acceptable
- no catastrophic subgroup failures
- inference is reliable
- expected_minutes_v1 integration is correct
- deterministic fallback exists

If ML does not convincingly beat the baseline:

KEEP:

xA_baseline_v1

and document:

"ML xA model NOT DEPLOYED — deterministic baseline retained."

Do not force deployment.

==================================================
21. PRODUCTION INTERFACE IF APPROVED
==================================================

If the model passes evaluation, create:

xa_predictor.py

Production output:

player_id
fixture_id
gameweek
xa_ml
model_version
used_fallback

The prediction must represent:

EXPECTED ASSISTS FOR THAT SINGLE FIXTURE.

For DGWs:

Fixture 1 xA
+
Fixture 2 xA
=
GW total xA

Do not aggregate inside the predictor.

==================================================
22. FALLBACK
==================================================

If the ML model:

- fails to load
- lacks required features
- produces invalid output
- inference fails

fall back to:

xA_baseline_v1

Return:

used_fallback=True

and:

model_version="xa_baseline_v1"

Do not silently return zero.

Log fallback events.

==================================================
23. PROJECTION ENGINE INTEGRATION
==================================================

If deployment is approved:

The projection pipeline becomes:

expected_minutes_v1
        │
        ├──────────────► xg_v1_lgbm
        │
        └──────────────► xA model
                              │
                              ▼
                       FPL scoring engine
                              │
                              ▼
                             xP

Do NOT modify:

- clean sheet
- DEFCON
- bonus
- optimizer

Ensure assists are not double-counted.

==================================================
24. DIAGNOSTICS
==================================================

Extend diagnostics to show:

Player
Gameweek
Fixture
Opponent
Home/Away

Expected Minutes
P(start)

xG
xG model version

Baseline xA
ML xA
xA model version
xA fallback status

Then:

Goal points
Assist points
Clean Sheet
DEFCON
Bonus
Total xP

This allows us to trace the complete prediction chain.

==================================================
25. CURRENT 2026/27 FORWARD PREDICTIONS
==================================================

After model selection, it is acceptable to run the model against the current 2026/27 database.

These are forward predictions only.

Do NOT use future 2026/27 outcomes for training.

Do NOT claim validation on 2026/27.

Show representative GW1 player-fixture xA predictions.

==================================================
26. MODEL VERSIONING
==================================================

If deployed, register:

xa_v1_lgbm

Preserve:

xA_baseline_v1

Record:

- model type
- target definition
- training seasons
- validation season
- test season
- feature list
- whether xG was used
- hyperparameters
- validation metrics
- test metrics
- calibration
- artifact location
- deployment date

Do not overwrite the baseline.

==================================================
27. TESTS
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
- non-negative xA
- sensible output bounds
- fallback behavior
- expected_minutes_v1 integration
- optional xG feature integration
- no double-counting
- diagnostics
- production projection integration if deployed

Run:

python -m pytest

All previous tests must continue to pass.

==================================================
28. DOCUMENTATION — MANDATORY
==================================================

Documentation is a permanent project requirement.

EVERY FUTURE DEVELOPMENT PHASE MUST UPDATE THE DOCUMENTATION.

Update:

docs/ROADMAP.md

docs/phases/PHASE_3B_EXPECTED_ASSISTS.md

docs/models/MODEL_REGISTRY.md

docs/models/ML_MODELS.md

docs/data/DATA_DICTIONARY.md

docs/data/DATA_PIPELINE.md if the dataset pipeline changes

docs/decisions/ARCHITECTURAL_DECISIONS.md if a new architectural decision is made

docs/README.md if necessary

Save this exact prompt as:

docs/prompts/PHASE_3B_EXPECTED_ASSISTS.md

Clearly distinguish:

- IMPLEMENTED
- TRAINED
- EVALUATED
- APPROVED
- DEPLOYED
- FALLBACK
- PLANNED

Do not describe xA ML as deployed unless the deployment decision is explicitly positive.

==================================================
29. FINAL REPORT
==================================================

Return a complete report containing:

1. Data sources inspected
2. Dataset size
3. Target definition
4. Feature list
5. Baseline methodology
6. Candidate formulations
7. Train/validation/test split
8. Leakage audit
9. DGW audit
10. Validation results
11. Test-set results
12. Baseline vs ML comparison
13. Calibration
14. Subgroup performance
15. Sanity checks
16. Error analysis
17. Feature importance
18. xG ablation result, if applicable
19. Production decision
20. Integration details if deployed
21. Fallback details
22. Model version
23. Tests
24. Documentation updates

Do not hide negative results.

If ML fails to beat the baseline, explicitly say:

"ML xA model NOT DEPLOYED — deterministic baseline retained."

==================================================
STOP CONDITION
==================================================

STOP AFTER PHASE 3B.

Do NOT begin Clean Sheet.

Do NOT begin DEFCON.

Do NOT begin Bonus.

Do NOT modify the optimizer.

Do NOT redesign the dashboard beyond diagnostics required for xA.

Wait for review of the Phase 3B results before proceeding.
