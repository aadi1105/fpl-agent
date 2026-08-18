FPL AI — OPTIMIZER MODES, PROGRESS TRACKING & POSITIONAL VALUE AUDIT

Do NOT start Phase 3C.

Do NOT train or modify any ML prediction models.

Do NOT change the underlying projection models.

Do NOT arbitrarily change optimizer weights to force different squads.

We have now fixed the expected-minutes role/transfer issue and the downstream projections have been recalculated.

The current frontend looks substantially healthier, but three issues now need to be addressed:

1. All optimization modes appear to return the exact same 15-man squad.
2. Long-running optimization/model operations provide no meaningful progress feedback.
3. The system needs better position-aware price/value diagnostics.

==================================================
1. FIX OPTIMIZATION MODE ROUTING
==================================================

Audit the complete path:

Frontend mode selector
→ API request
→ request payload
→ backend mode parsing
→ optimizer configuration
→ objective formulation
→ optimization result
→ frontend rendering

Verify that the selected mode is actually passed through every layer.

Log the selected mode during optimization.

For every mode, log:

mode
objective coefficients
budget
horizon
bench treatment
starting XI objective
squad objective

Do NOT modify the objectives yet.

First determine whether the mode is actually being applied.

==================================================
2. VERIFY ALL FOUR MODES INDEPENDENTLY
==================================================

Run all modes against EXACTLY THE SAME projection snapshot.

Modes:

CURRENT_GW_PLUS_3
STRONG_XI_DUMP_BENCH
BALANCED_BENCH
MAXIMUM_SQUAD

For each return:

Mode
15-man squad
Starting XI
Bench
Formation
Budget used
Bank
GW0 xP
GW0 captain-adjusted xP
GW0–GW3 weighted score

Also return:

objective value
solver status
solver runtime

Do not compare runs using freshly regenerated projections.

The projections must be identical across mode comparisons.

==================================================
3. DETERMINE WHY MODES CURRENTLY COLLAPSE
==================================================

If all four modes produce the same squad, investigate which of the following is occurring:

A. Mode is not reaching backend.
B. Mode is reaching backend but ignored.
C. Mode changes configuration but not objective.
D. Objectives are mathematically equivalent.
E. Frontend is displaying cached/default results.
F. Other.

Do not guess.

Produce evidence from logs/tests.

If objectives are genuinely equivalent, explain mathematically why.

Do NOT force different outputs simply to make the UI look different.

==================================================
4. MODE-SPECIFIC ACCEPTANCE TESTS
==================================================

Create tests that verify mode behavior.

CURRENT_GW_PLUS_3:
- squad objective uses 55/20/15/10 weighting
- current XI maximizes GW0 only

STRONG_XI_DUMP_BENCH:
- materially prioritizes starting XI strength
- bench expenditure is minimized subject to valid squad constraints

BALANCED_BENCH:
- starting XI remains strong
- bench has useful minutes security
- bench quality contributes according to its explicitly defined objective

MAXIMUM_SQUAD:
- maximizes overall squad horizon rather than concentrating purely on GW0

Do not assume every mode MUST produce a different squad.

However, if the same squad is genuinely optimal under multiple modes, report that.

The test should verify that changing the mode changes the mathematical problem, not necessarily that it always changes the answer.

==================================================
5. ADD A REAL OPTIMIZATION PROGRESS SYSTEM
==================================================

Implement genuine progress reporting.

Do NOT create a fake timer-based progress bar.

Long-running operations should expose actual stages.

Recommended stages:

1. Loading FPL data
2. Loading model artifacts
3. Generating fixture-aware projections
4. Calculating xP
5. Building optimizer problem
6. Solving squad optimization
7. Selecting current GW XI
8. Selecting captain/vice-captain
9. Generating diagnostics
10. Finalizing result

Expose:

job_id
status
stage
stage_number
total_stages
progress_percent
message
players_processed where applicable
total_players where applicable
elapsed_time
error if failed

Use a background job/task architecture if necessary so the frontend does not block waiting for one long HTTP request.

Suggested API structure:

POST /api/v1/optimize/squad
→ returns job_id

GET /api/v1/optimize/status/{job_id}
→ returns current progress

GET /api/v1/optimize/result/{job_id}
→ returns completed result

Use the project's existing architecture where appropriate rather than introducing unnecessary infrastructure.

==================================================
6. FRONTEND PROGRESS UI
==================================================

When an optimization/model run is active, display something like:

FPL AI OPTIMIZER

████████████████░░░░ 80%

Step 7/10
Selecting current GW starting XI

Players processed: 590 / 590
Elapsed: XXs

The progress must reflect actual backend state.

On completion:

✓ Optimization complete

Show runtime.

On failure:

✕ Optimization failed

Show a useful error message.

Prevent duplicate optimizer submissions while a job is running.

==================================================
7. POSITION-AWARE PRICE MODEL / DIAGNOSTICS
==================================================

Important conceptual requirement:

FPL prices are position-specific.

A £6.0m player means very different things depending on position.

Examples:

£6.0m GKP → expensive goalkeeper
£6.0m DEF → relatively expensive defender
£6.0m MID → budget midfielder
£6.0m FWD → budget forward

The optimizer must continue to use the actual FPL price as the budget cost.

Do NOT add arbitrary rules such as:
"forwards should be more expensive."

The budget itself already handles this.

Instead, add position-aware VALUE diagnostics.

For every player calculate:

xP
price
xP per £m
position
position price percentile
position xP percentile
position value percentile

Price percentile MUST be calculated relative to players in the same position.

Example:

Raya £6.0m:
→ goalkeeper price percentile

Gabriel £8.0m:
→ defender price percentile

Igor Jesus £6.0m:
→ forward price percentile

Do not compare raw price percentiles across positions.

==================================================
8. POSITION-AWARE PROJECTION SANITY CHECKS
==================================================

Verify that:

- goalkeeper scoring uses goalkeeper rules
- defender scoring uses defender rules
- midfielder scoring uses midfielder rules
- forward scoring uses forward rules

Verify that price is NOT being used as a direct proxy for starting probability.

Price may be used as:

- budget cost
- value analysis
- position-relative pricing diagnostics

But it must not imply:

"expensive = likely to start."

This is especially important after the previous expected-minutes bug.

==================================================
9. VALUE DIAGNOSTICS
==================================================

Add a player diagnostic view containing:

Player
Position
Price
xP
xP / £m
Position price percentile
Position xP percentile
Position value percentile
Expected minutes
P(start)

This is diagnostic information.

Do NOT replace the optimizer's objective with xP/£m.

The primary optimizer objective remains expected FPL points subject to the FPL constraints.

==================================================
10. FRONTEND MODE COMPARISON
==================================================

Add a comparison view/table:

MODE
15-MAN SQUAD
STARTING XI
BENCH
FORMATION
BUDGET
BANK
GW0 xP
GW0 CAPTAIN BONUS
4-GW WEIGHTED SCORE
RUNTIME

Allow the user to compare all four modes using the SAME projection snapshot.

This should make it obvious whether the modes genuinely differ.

==================================================
11. TESTING
==================================================

Add tests for:

- selected mode reaches backend
- mode-specific configuration is applied
- identical projections are used for comparison
- mode objectives differ where intended
- valid formation constraints
- budget constraints
- progress state transitions
- job completion
- job failure
- duplicate job prevention
- position-specific price percentile
- xP/£m calculation
- position-specific value ranking
- price does not directly determine P(start)

Run the full test suite.

==================================================
12. DOCUMENTATION
==================================================

Update documentation.

EVERY DEVELOPMENT PHASE MUST UPDATE DOCUMENTATION.

Update appropriate:

docs/phases/
docs/models/
docs/data/
docs/decisions/
docs/ROADMAP.md

Document:

- optimizer mode architecture
- why modes previously collapsed
- final objective definitions
- progress/job architecture
- position-aware value metrics
- design decisions
- limitations

Save this prompt as:

docs/prompts/OPTIMIZER_MODES_PROGRESS_POSITIONAL_VALUE.md

==================================================
13. IMPORTANT STOP CONDITION
==================================================

Do NOT begin Phase 3C.

Do NOT modify ML models.

Do NOT change optimizer objectives merely to produce visually different squads.

Do NOT force every mode to return a different team.

First diagnose the current behavior and implement the infrastructure correctly.

At the end return:

1. Root cause of identical modes
2. Evidence
3. Fix
4. Mode comparison results
5. Progress implementation
6. Position-aware value diagnostics
7. Tests
8. Documentation changes
9. Remaining issues
10. Recommendation on whether we are ready to proceed to Phase 3C

STOP and wait for review.
