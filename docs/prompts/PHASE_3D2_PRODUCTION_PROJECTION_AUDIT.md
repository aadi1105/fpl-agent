PHASE 3D.2 — PRODUCTION PROJECTION & FIXTURE PIPELINE FORENSIC AUDIT

IMPORTANT TERMINOLOGY:

FPL Gameweeks start at GW1.

There is NO GW0.

Use the following terminology throughout the code, API, frontend, tests, documentation, and reports:

- GW1 = current/target gameweek
- GW2 = next gameweek
- GW3 = second upcoming gameweek
- GW4 = third upcoming gameweek

The default 4-gameweek weighted horizon is:

55% GW1
20% GW2
15% GW3
10% GW4

If the existing code uses "GW0" to represent the current gameweek, treat this as a naming/terminology issue and document it. Do NOT silently reinterpret GW0 as an actual FPL gameweek.

==================================================
PURPOSE
==================================================

STOP before making any modelling or optimizer changes.

We have completed Phase 3D.1.

Phase 3D.1 established that the previously observed Bruno Fernandes price discrepancy was caused by a diagnostic-report player-matching bug, NOT by the production price pipeline.

The canonical production price pipeline is now verified.

However, Phase 3D.1 revealed a much more serious projection discrepancy that must be investigated before we proceed.

The objective of Phase 3D.2 is to perform a READ-ONLY forensic audit of the entire production prediction pipeline and determine exactly where the current player projections are coming from.

DO NOT:

- retrain models
- modify model weights
- modify optimizer objectives
- manually boost players
- manually downgrade players
- hard-code Bruno Fernandes
- hard-code Haaland
- add ownership bonuses
- add FPL consensus bonuses
- manipulate fixture difficulty
- manipulate prices
- manually edit player projections

Do not try to make the squad look more like the FPL template.

The objective is to identify the actual root cause of the projection discrepancies.

==================================================
PHASE 3D.1 FINDINGS
==================================================

Phase 3D.1 confirmed:

Canonical price source:

Official FPL API
→ Player.now_cost
→ SQLite database
→ Projection Engine
→ Optimizer
→ API
→ Frontend

All 590 active players matched the canonical price.

The Bruno price discrepancy was caused by the Phase 3D diagnostic script using:

df['web_name'].str.contains('Bruno Fernandes')

Official FPL data stores Bruno Fernandes as:

B.Fernandes

The fallback search for "Bruno" incorrectly selected Bruno Guimarães.

This has been fixed using canonical Player IDs.

Therefore:

Bruno Fernandes:
Player ID = 426
Price = £12.0m
Ownership = 48.6%

Bruno Guimarães:
Player ID = 452
Price = £7.0m
Ownership = 9.3%

The production price pipeline is NOT currently suspected to be the problem.

==================================================
CRITICAL PROJECTION DISCREPANCY
==================================================

Phase 3D previously reported approximately:

Haaland:
GW1 xP ≈ 8.12

However, the current frontend subsequently showed:

Haaland:
GW1 xP ≈ 4.22

Phase 3D.1's corrected canonical diagnostic table then reported:

Haaland:
£15.5m
71.4% ownership
v2 GW1 xP = 1.47
Model Rank #536

Bruno Fernandes:
£12.0m
48.6% ownership
v2 GW1 xP = 2.01
Model Rank #293

Gabriel:
£8.0m
v2 GW1 xP = 4.18
Model Rank #17

Awoniyi:
£5.5m
v2 GW1 xP = 1.28
Model Rank #578

Osula:
£6.0m
v2 GW1 xP = 1.23
Model Rank #584

João Pedro:
£7.5m
v2 GW1 xP = 1.47
Model Rank #536

Calvert-Lewin:
£6.0m
v2 GW1 xP = 1.48
Model Rank #534

Therefore we currently have an unexplained discrepancy:

Haaland:
approximately 8.12
→ approximately 4.22
→ 1.47

These values must NOT be assumed to be correct.

Determine exactly where this discrepancy originates.

==================================================
PART 1 — TRACE PLAYERS END-TO-END
==================================================

Trace the following players through the COMPLETE production pipeline:

- Erling Haaland
- Bruno Fernandes
- Mohamed Salah
- Cole Palmer
- Bukayo Saka
- Gabriel Magalhães
- João Pedro
- Dominic Calvert-Lewin
- Taiwo Awoniyi
- William Osula
- Riccardo Calafiori
- Antoine Semenyo

For each player trace:

Official FPL API data
→ database player record
→ current club
→ GW1 fixture
→ GW2 fixture
→ GW3 fixture
→ GW4 fixture
→ fixture difficulty
→ team strength ratings
→ opponent strength ratings
→ expected minutes model
→ xG model
→ xA model
→ clean-sheet model
→ DEFCON model
→ bonus model
→ negative-event model
→ FPL scoring engine
→ GW1 xP
→ GW2 xP
→ GW3 xP
→ GW4 xP
→ weighted 4-GW score
→ optimizer input
→ optimizer output
→ frontend output

Create a machine-readable diagnostic record for every audited player.

==================================================
PART 2 — IDENTIFY THE ACTUAL RUNTIME MODEL VERSIONS
==================================================

Determine exactly which model artifacts are being loaded by the running production application.

Check:

Expected Minutes:
- expected_minutes_v1
- expected_minutes_v2

xG:
- xg_v1_lgbm
- xg_v2 candidate/production artifact

xA:
- xa_v1_lgbm
- xa_v2 candidate/production artifact

Clean Sheet:
- cs_v1_lgbm or current production artifact

DEFCON:
- defcon_v1_poisson or current production artifact

For every loaded artifact report:

- exact filename
- exact filesystem path
- model version
- SHA256 hash
- training dataset/version if recorded
- feature schema
- whether artifact loaded successfully
- whether fallback was used

Do NOT trust the frontend architecture banner as proof of deployment.

Verify what the backend actually loads at runtime.

If the frontend says v2 but the backend loads v1, identify that discrepancy.

If the backend says v2 but actually loads a v1 artifact, identify that discrepancy.

Do not simply change the label.

==================================================
PART 3 — RECONCILE PHASE 3D RESULTS
==================================================

Find the exact code/data path that generated the Phase 3D reported Haaland projection.

Reproduce the Phase 3D calculation for:

Haaland
Bruno
Gabriel
Awoniyi
Osula

Then reproduce the CURRENT production calculation for the exact same player, gameweek, fixture and database state.

Compare every intermediate value.

Produce a table:

Player
Phase 3D GW1 xP
Phase 3D intermediate values
Current production GW1 xP
Current intermediate values
Difference
Root cause

The goal is to explain the discrepancy rather than simply reporting it.

==================================================
PART 4 — VERIFY GW1-GW4 FIXTURE MAPPING
==================================================

Verify that every player receives the correct fixtures for:

GW1
GW2
GW3
GW4

For each fixture verify:

- fixture ID
- gameweek
- player team ID
- player team name
- opponent team ID
- opponent team name
- home/away
- kickoff if available
- fixture difficulty
- team attacking rating
- team defensive rating
- opponent attacking rating
- opponent defensive rating

Specifically verify:

HAALAND:

Manchester City → GW1 opponent
Manchester City → GW2 opponent
Manchester City → GW3 opponent
Manchester City → GW4 opponent

BRUNO FERNANDES:

Manchester United → GW1 opponent
Manchester United → GW2 opponent
Manchester United → GW3 opponent
Manchester United → GW4 opponent

Verify that the current 2026/27 FPL fixture data is being used.

Detect:

- stale previous-season fixtures
- incorrect team IDs
- incorrect player-team mapping
- incorrect home/away interpretation
- incorrect gameweek assignment
- duplicate fixtures
- missing fixtures
- fixtures from the wrong season
- incorrect opponent mapping

==================================================
PART 5 — VERIFY FIXTURE IMPACT ON PROJECTIONS
==================================================

Fixtures must actually influence the prediction inputs.

For each audited player and each GW1-GW4 fixture show:

Opponent
Home/Away
Fixture Difficulty
Team Attacking Rating
Opponent Defensive Rating
Attacking Modifier
Base xG
Fixture-adjusted xG
Base xA
Fixture-adjusted xA
Clean Sheet Probability
DEFCON Probability
Expected Minutes
Final xP

Do NOT merely verify that the frontend displays different fixture names.

Verify mathematically that fixture information is actually being consumed by the production projection engine.

For example:

A strong attacking team against a weak defence should generally produce a different attacking projection than the same player against an elite defence.

A strong defensive team against a weak attack should generally produce a different clean-sheet projection.

==================================================
PART 6 — VERIFY EXPECTED MINUTES
==================================================

For every audited player record:

- P(start)
- P(60+)
- P(0)
- expected minutes
- historical minutes
- recent minutes
- recent starts
- current-club evidence
- transfer status
- fallback usage
- model version

Pay particular attention to:

Awoniyi
Osula
Marmoush
Bruno
Haaland
João Pedro
Calvert-Lewin

Determine whether unexpectedly low/high xP is actually being caused by expected minutes.

Do NOT modify the minutes model.

==================================================
PART 7 — VERIFY xG AND xA
==================================================

For every audited player record:

- xG/90
- xA/90
- sample size
- shrinkage factor
- recent xG
- recent xA
- long-term xG
- long-term xA
- current-club xG/xA
- previous-club xG/xA
- model prediction before fixture adjustment
- model prediction after fixture adjustment

Verify that Phase 3C.8 shrinkage is actually being used if v2 is supposed to be deployed.

Do not assume the model artifact name proves that.

==================================================
PART 8 — MANUALLY RECONSTRUCT FPL SCORING
==================================================

For Haaland and Bruno, manually reconstruct the GW1 expected points.

Show:

Expected Minutes
Appearance points
Expected goals
Expected goal points
Expected assists
Expected assist points
Clean-sheet points
DEFCON
Bonus
Cards/negative events
Other components
FINAL GW1 xP

Verify:

sum(all components) == final GW1 xP

Verify positional FPL scoring:

DEF goal = 6 points
MID goal = 5 points
FWD goal = 4 points

Verify that captaincy is applied ONLY after base GW1 xP is calculated.

Captaincy must never contaminate the player's base projection.

==================================================
PART 9 — VERIFY CURRENT PRICE DATA
==================================================

Although Phase 3D.1 passed the price integrity audit, perform a lightweight verification while tracing the players.

Canonical source remains:

Official FPL API
→ Player.now_cost

Verify:

Haaland = £15.5m
Bruno Fernandes = £12.0m
Palmer = £9.5m
Saka = £9.5m
Gabriel = £8.0m
Semenyo = £8.5m
Awoniyi = £5.5m
Osula = £6.0m
João Pedro = £7.5m
Calvert-Lewin = £6.0m

Do NOT create another price source.

==================================================
PART 10 — VERIFY OPTIMIZER INPUTS
==================================================

Print the exact optimizer input for:

Haaland
Bruno Fernandes
Salah
Palmer
Saka
Gabriel
Calafiori
Awoniyi
Osula
João Pedro
Calvert-Lewin
Semenyo

For each include:

- price
- position
- club
- GW1 xP
- GW2 xP
- GW3 xP
- GW4 xP
- weighted 4-GW score
- expected minutes GW1
- P(start) GW1

Then verify that the optimizer is actually using these values.

The optimizer must NOT be using:

- stale xP
- old model predictions
- historical prices
- diagnostic-only values
- cached projections
- a different gameweek
- GW0 data

==================================================
PART 11 — INDEPENDENT RANKING SANITY CHECK
==================================================

Using ONLY the exact production GW1 xP values passed to the optimizer:

Calculate:

1. All-player GW1 xP ranking
2. Top players by weighted GW1-GW4 score
3. Players selected by optimizer
4. Players displayed by frontend

These must be internally consistent.

If Haaland is genuinely 1.47 or 4.22, determine exactly why.

If Haaland is actually 8.12 upstream but 4.22 downstream, identify where the value changes.

If Bruno is genuinely 2.01, determine exactly why.

Do not alter the numbers to make them look more realistic.

==================================================
PART 12 — FRONTEND VS BACKEND AUDIT
==================================================

For the exact same request/session compare:

Backend response
vs
Frontend display.

Check:

- model version
- player ID
- player name
- price
- club
- fixture
- GW1 xP
- GW2 xP
- GW3 xP
- GW4 xP
- weighted score
- expected minutes
- P(start)

Specifically compare:

Haaland
Bruno Fernandes
Gabriel
Awoniyi
Osula

The frontend must display exactly what the backend returns.

If it does not, identify the transformation causing the discrepancy.

==================================================
PART 13 — OPTIMIZER SEPARATION TEST
==================================================

Do a READ-ONLY diagnostic run using the exact current production projections.

Do NOT modify optimizer code.

Report:

A. Top 20 players by GW1 xP

B. Top 20 players by weighted GW1-GW4 score

C. Current optimizer squad

D. Current GW1 starting XI

E. Bench

F. Captain

G. Vice-captain

Then explain mathematically why each surprising player is selected.

Do not insert Bruno.

Do not remove Awoniyi.

Do not remove Osula.

Do not manually manipulate any player.

==================================================
PART 14 — BRUNO FERNANDES SPECIFIC INVESTIGATION
==================================================

Bruno is NOT being hard-coded as a required pick.

Instead determine why the current production system ranks him where it does.

Audit:

- current price
- ownership
- expected minutes
- P(start)
- xG
- xA
- recent xG/xA
- historical xG/xA
- current-club role
- penalty involvement if available
- set-piece involvement if available
- attacking position
- Manchester United attacking strength
- opponent defensive strength
- GW1 fixture
- GW2 fixture
- GW3 fixture
- GW4 fixture
- bonus probability
- negative-event probability
- final GW1 xP
- weighted GW1-GW4 score

Compare Bruno directly against:

Haaland
Semenyo
Mbeumo
Palmer
Gibbs-White
João Pedro
Calvert-Lewin

If Bruno remains low, classify the cause:

A. Model correctly identifies lower expected output
B. Missing predictive feature
C. Data quality problem
D. Role/minutes problem
E. Fixture/team-strength problem
F. Projection/scoring bug
G. Runtime/model-version mismatch
H. Other

Do NOT modify the model to force Bruno upward.

==================================================
PART 15 — HAALAND SPECIFIC INVESTIGATION
==================================================

Because Haaland has produced radically different reported values across phases, perform a full calculation audit.

Reconstruct his GW1 projection from raw inputs.

Report:

- expected minutes
- P(start)
- xG
- xA
- fixture
- opponent
- team attacking rating
- opponent defensive rating
- fixture modifier
- goal expectation
- assist expectation
- appearance expectation
- bonus expectation
- final xP

Then identify exactly why the system reports:

Phase 3D ≈ 8.12
Current frontend ≈ 4.22
Phase 3D.1 ≈ 1.47

If one of those values came from an incorrectly generated diagnostic dataset, identify it explicitly.

==================================================
PART 16 — CONSENSUS AS DIAGNOSTIC ONLY
==================================================

Use current FPL ownership only as an external diagnostic signal.

Do NOT add ownership directly into xP.

Do NOT multiply xP by ownership.

Do NOT force popular players into the optimizer.

Instead calculate:

Model Rank
Consensus Rank
Ownership
Rank Difference

Then investigate major disagreements.

Particularly inspect:

Bruno
João Pedro
Calvert-Lewin
Haaland
Awoniyi
Osula
Marmoush

The purpose is to identify missing information or genuine model disagreement.

==================================================
PART 17 — TRANSFER / CURRENT-CLUB ROLE CHECK
==================================================

Verify transferred players.

Historical performance can inform underlying ability.

Historical performance must NOT automatically imply current-club starting probability.

Current-club evidence must control current role/minutes estimates.

Specifically audit:

- Marmoush
- João Pedro
- Calvert-Lewin
- Awoniyi
- Osula
- other recently transferred players

Do not manually blacklist players.

Use general transfer-aware logic.

==================================================
PART 18 — DOUBLE GAMEWEEK CHECK
==================================================

Maintain per-fixture predictions.

Each individual fixture must produce:

0–90 expected minutes.

A Double Gameweek must be:

Fixture A prediction
+
Fixture B prediction

Never one 0–180 minute prediction.

Verify this remains true.

==================================================
PART 19 — TERMINOLOGY CLEANUP
==================================================

Search the project for incorrect usage of "GW0".

FPL gameweeks begin at GW1.

Replace incorrect user-facing terminology such as:

GW0
GW0 xP
GW0 Fixture
GW0 weighting

with:

GW1
GW1 xP
GW1 Fixture
GW1 weighting

ONLY do this where GW0 is being used as an incorrect alias for the current FPL gameweek.

Do NOT alter historical dataset IDs or internal database keys blindly.

If an internal identifier genuinely requires GW0 for technical reasons, document the mapping clearly:

internal identifier → actual FPL GW1.

The user-facing system must consistently show GW1-GW4.

==================================================
PART 20 — OUTPUT
==================================================

Produce a forensic report containing:

1. Actual runtime model versions
2. Artifact paths and hashes
3. Phase 3D projection values
4. Phase 3D.1 corrected values
5. Current production values
6. Exact source of every discrepancy
7. Fixture mapping verification
8. Team-strength verification
9. Expected-minutes verification
10. xG verification
11. xA verification
12. FPL scoring verification
13. Price verification
14. Optimizer-input verification
15. Backend/frontend verification
16. Bruno investigation
17. Haaland investigation
18. Consensus comparison
19. Transfer handling
20. DGW handling
21. GW0 terminology audit
22. Test results
23. Root causes
24. Recommended fixes

For every discovered problem distinguish:

DATA BUG
MODEL BUG
FEATURE BUG
FIXTURE BUG
SCORING BUG
RUNTIME ARTIFACT BUG
API BUG
FRONTEND BUG
REPORTING BUG
OPTIMIZER BUG
TERMINOLOGY BUG

==================================================
STRICT STOP CONDITION
==================================================

DO NOT:

- retrain models
- modify model weights
- modify optimizer objectives
- modify formation constraints
- modify captaincy logic
- add ownership bonuses
- hard-code Bruno
- hard-code Haaland
- manually alter projections
- manipulate fixture difficulty
- manipulate prices

First identify the root cause.

Only after the root cause is clearly identified should you propose code changes.

If a code fix is necessary, explain:

1. What is broken
2. Why it is broken
3. Which file/function is responsible
4. What the proposed fix changes
5. What the fix does NOT change
6. How it will be tested

Do not implement unrelated improvements.

==================================================
DOCUMENTATION
==================================================

Create:

docs/phases/PHASE_3D2_PRODUCTION_PROJECTION_AUDIT.md

Save this exact prompt:

docs/prompts/PHASE_3D2_PRODUCTION_PROJECTION_AUDIT.md

Update:

docs/ROADMAP.md
docs/DATA_PIPELINE.md
docs/PHASE_3D_PRODUCTION_MODEL_VALIDATION.md

Continue maintaining the central documentation structure established earlier.

Every future phase must continue updating the documentation and saving its prompt.

==================================================
FINAL REQUIREMENT
==================================================

STOP after completing the forensic audit and identifying the root cause.

Do not proceed to the next modelling phase.

Do not redesign the optimizer.

Do not attempt to make the resulting squad "look right".

The immediate objective is:

BUILD TRUST IN THE PRODUCTION PROJECTION PIPELINE.

Only once we know exactly what numbers the system is producing, where they came from, and why they differ from previous validated results should we proceed.
