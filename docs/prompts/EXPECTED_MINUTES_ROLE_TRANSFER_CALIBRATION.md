FPL AI — EXPECTED MINUTES ROLE & TRANSFER CALIBRATION

Do NOT start Phase 3C.

Do NOT modify:
- xG model
- xA model
- Clean Sheet model
- DEFCON model
- Bonus model
- optimizer objectives
- squad selection logic

We have identified a serious issue in expected_minutes_v1.

The current low-sample fallback can give players with little or no current-club role evidence approximately 65–80 expected minutes and ~85–90% start probability based largely on price tier.

This is causing fringe/transferred/young players to receive unrealistic xP and can distort the optimizer.

Example:
Reiss Nelson is Arsenal-contracted but had only ~118 relevant historical minutes in the audited sample, yet was projected around 75.9 minutes with an 88.1% start probability.

The goal is NOT to hard-code Nelson.

The goal is to make the expected-minutes system correctly infer current role for ALL players.

==================================================
1. AUDIT THE CURRENT MINUTES PIPELINE
==================================================

Before changing anything, inspect and document:

- expected_minutes_v1 features
- current-club features
- historical minutes features
- starts_last_5
- average_minutes_last_5
- current-club minutes
- current-club starts
- current-club appearances
- transfer/loan handling
- low-sample detection
- fallback logic
- price-tier fallback
- P(start) calculation
- expected-minutes calculation

Identify exactly why low-current-evidence players receive high expected minutes.

Do not guess.

==================================================
2. SEPARATE PLAYER HISTORY FROM CURRENT ROLE
==================================================

Historical player ability and current role must be treated separately.

Historical player statistics may carry across clubs where appropriate.

But historical minutes/starts at a previous club must NOT automatically imply the same role at the player's current club.

For every player-fixture, distinguish:

PLAYER HISTORY
- historical minutes
- historical starts
- xG/90
- xA/90

CURRENT CLUB ROLE
- current-club minutes
- current-club starts
- current-club appearances
- recent current-club minutes
- recent current-club starts
- current role evidence

FIXTURE CONTEXT
- current club
- opponent
- home/away
- fixture

Do not relabel historical club data.

==================================================
3. ADD CURRENT-ROLE FEATURES
==================================================

Where supported by the existing historical data, add features such as:

- current_club_minutes
- current_club_starts
- current_club_appearances
- current_club_minutes_last_1
- current_club_minutes_last_3
- current_club_minutes_last_5
- current_club_starts_last_3
- current_club_starts_last_5
- current_club_evidence_level
- transfer/club-change indicator

Ensure all features are strictly pre-deadline.

No future information.

No data leakage.

Do NOT invent unavailable current-club information.

==================================================
4. REPLACE THE PRICE-BASED ROLE FALLBACK
==================================================

The current fallback effectively does:

low sample + player price
→ assumed starter-like minutes

This is not acceptable.

Remove/revise this behavior.

Price must NOT be used as a proxy for probability of starting.

If current-role evidence is insufficient, the system should become appropriately conservative rather than assuming the player is a starter.

Do NOT arbitrarily hard-code Nelson, Dowman, Reed, or any other individual.

If a fallback is required, derive it from historical evidence/backtesting rather than intuition.

Document the fallback mathematically.

==================================================
5. USE SHRINKAGE / UNCERTAINTY WHERE APPROPRIATE
==================================================

Investigate a statistically defensible way to handle sparse current-role evidence.

A suitable approach may be shrinkage:

estimated_role =
    evidence_weight × observed_current_role
    + (1 - evidence_weight) × conservative_prior

The exact formulation and parameters must be determined from historical data and validation.

Do NOT simply choose arbitrary weights because they make the current GW1 squad look better.

The purpose is generalization.

==================================================
6. TRANSFER / LOAN EDGE CASES
==================================================

Explicitly test players who:

- transferred clubs
- were loaned out
- returned from loan
- joined a new club
- were promoted from youth teams
- had very little current-club evidence
- had large historical minutes at a previous club

For these players determine whether the system correctly distinguishes:

"known player ability"

from:

"known current playing role."

A player can have strong historical attacking statistics while simultaneously having very low current expected minutes.

That is valid.

==================================================
7. REISS NELSON SANITY CHECK
==================================================

Use Reiss Nelson as a diagnostic case, NOT a hard-coded exception.

Verify:

- current club
- previous club
- historical minutes
- current-club evidence
- expected minutes
- P(start)
- P(60+)
- P(0)

The revised system should produce a result consistent with the available evidence.

Do not force a specific number.

The important requirement is that the model no longer assumes a starter role simply because he is registered to a strong club or has a £5.5m price.

==================================================
8. BACKTEST THE REVISED SYSTEM
==================================================

Retrain/recalibrate expected_minutes only if necessary.

Use a strict temporal out-of-sample evaluation.

Compare:

expected_minutes_v1
vs
revised expected-minutes model

Evaluate overall and specifically on:

1. All players
2. <300 historical minutes
3. <600 historical minutes
4. Transfers
5. Returning loanees
6. Players with little/no current-club evidence
7. Established starters

Use appropriate metrics already supported by the project, including:

- MAE
- RMSE
- Poisson deviance if applicable
- P(start) LogLoss
- calibration
- subgroup performance

The revised system must NOT merely improve fringe players while damaging established starters.

==================================================
9. SANITY CHECK THE OUTPUT DISTRIBUTION
==================================================

After recalibration, inspect:

- distribution of expected minutes
- distribution of P(start)
- distribution of P(60+)
- distribution of P(0)

Specifically identify:

- £4.5–£6.0m players with >70 expected minutes
- players with P(start) >80% despite very little current-club evidence
- players with <20% P(start) but >60 expected minutes
- transferred players receiving starter-level minutes without current-club evidence

Do not assume every flagged player is wrong.

Investigate each category.

==================================================
10. DOWNSTREAM RECOMPUTATION
==================================================

Once the revised minutes system is validated:

Recalculate:

expected minutes
→ xG projections
→ xA projections
→ final xP

using the EXISTING xG and xA models.

Do NOT retrain xG or xA unless the audit proves that their models themeselves are defective.

The purpose is to see how fixing minutes propagates through the existing pipeline.

==================================================
11. OPTIMIZER CHECK — READ ONLY
==================================================

After recalculating projections, run the existing optimizer.

Do NOT modify the optimizer.

Compare:

- old squad
- revised squad
- budget used
- GW0 xP
- weighted 4-GW score
- cheap-player rankings

We expect the optimizer to change naturally if the projections improve.

If it does not, document why.

==================================================
12. FRONTEND
==================================================

Update the player diagnostics UI to expose:

Expected Minutes
P(start)
P(60+)
P(0)

Current-club evidence
Historical minutes
Current-club minutes
Current-club starts
Transfer/role indicator where available

This is necessary so we can understand why the system believes a player will start.

Do not clutter the main dashboard unnecessarily.

Put detailed role evidence in the player diagnostic view.

==================================================
13. TESTS
==================================================

Add regression tests for:

- price is not used as a direct proxy for starting probability
- previous-club minutes do not become current-club minutes
- current-club features preserve club identity
- transfer boundary handling
- sparse current-club evidence
- low-sample players
- expected minutes remains within 0–90 per fixture
- DGWs remain represented per fixture
- no future information enters features
- existing production behavior for established starters remains valid

Run the complete test suite.

==================================================
14. ACCEPTANCE CRITERIA
==================================================

Do NOT declare success merely because Nelson's xP became lower.

The revised system passes only if:

1. It handles low-current-evidence players conservatively.
2. It handles transfers without carrying over role assumptions incorrectly.
3. It does not rely on price as a starting-probability proxy.
4. It maintains or improves out-of-sample performance.
5. Established starters are not materially degraded.
6. No temporal leakage exists.
7. Existing xG/xA models remain compatible.
8. DGW handling remains correct.
9. All tests pass.
10. The optimizer can consume the revised projections without modification.

==================================================
15. DOCUMENTATION
==================================================

Update the project documentation.

Remember:

EVERY DEVELOPMENT PHASE MUST UPDATE THE DOCUMENTATION.

Update the appropriate:

docs/phases/
docs/models/
docs/data/
docs/decisions/
docs/ROADMAP.md

Document:

- root cause
- old behavior
- revised approach
- mathematical formulation
- features added
- fallback changes
- transfer handling
- backtest results
- subgroup results
- limitations
- deployment decision

Clearly label:

FINDING
FIXED
NOT FIXED
LIMITATION
DECISION

Save this prompt as:

docs/prompts/EXPECTED_MINUTES_ROLE_TRANSFER_CALIBRATION.md

==================================================
FINAL REPORT
==================================================

Return:

1. Root cause
2. Exact code/data changes
3. Revised feature list
4. Revised fallback logic
5. Transfer handling
6. Nelson diagnostic before vs after
7. Backtest metrics
8. Subgroup metrics
9. Sanity-check results
10. Downstream xG/xA/xP changes
11. Optimizer before vs after
12. Tests
13. Documentation updated
14. Remaining limitations
15. Recommendation on whether Phase 3C can begin

STOP after this phase.

Do NOT begin Phase 3C automatically.
