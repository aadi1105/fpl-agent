# PHASE 3C.6 — EXPECTED MINUTES, ROLE & SAMPLE-SIZE SANITY AUDIT

We are NOT changing the production prediction pipeline in this phase.

Phase 3C.5 found major model-vs-consensus disagreements, particularly:

- Awoniyi: Model #3, consensus #43, 0.5% ownership, model xP 5.66
- Osula: Model #7, consensus #29, 1.1% ownership, model xP 5.13
- Marmoush: Model #2, consensus #18, 3.2% ownership, model xP 6.85
- Beto: Model #12, consensus #48, 0.4% ownership, model xP 5.12

Phase 3C.5 identified a recurring pattern:

HIGH HISTORICAL PER-90 EFFICIENCY
+
LIMITED / UNCERTAIN SAMPLE
+
HIGH EXPECTED MINUTES
=
POTENTIALLY EXCESSIVE xP

Awoniyi and Osula were specifically classified as:

C. Expected-Minutes / Role Issue

with:

High Per-90 Extrapolation Risk

The purpose of this phase is to determine EXACTLY why these players are being projected so highly and whether this represents a general statistical weakness in the current pipeline.

This is a READ-ONLY diagnostic investigation.

==================================================
1. STRICT BOUNDARIES FOR THIS PHASE
==================================================

Do NOT modify:
- expected_minutes_v1
- xG model
- xA model
- Clean Sheet model
- DEFCON model
- scoring engine
- player projections
- optimizer
- optimizer objectives
- model weights
- training datasets

Do NOT retrain any models.

Do NOT manually override any player values.

External FPL information may ONLY be used as diagnostic evidence.

The goal is: "Understand why the model produces this result."
NOT: "Make the model agree with FPL consensus."

==================================================
2. AUDIT TARGET PLAYERS
==================================================

Perform detailed diagnostic breakdown for the following players:

Primary targets:
1. Taiwo Awoniyi
2. William Osula

Secondary high-differentials:
3. Omar Marmoush
4. Beto

Established comparisons (stable high minutes):
5. Erling Haaland
6. Alexander Isak
7. Ollie Watkins
8. Dominic Solanke
9. Chris Wood

Template comparisons (lower model rank than market):
10. João Pedro
11. Dominic Calvert-Lewin

==================================================
3. PIPELINE DIAGNOSTIC AUDIT
==================================================

For EACH of the 11 target players, extract:

1. Final Projected xP
2. Component xP (apps, goals, assists, clean sheet, bonus, yellow cards, red cards)
3. Model Expected Minutes
4. P(start), P(60+), P(0)
5. Historical Minutes (current club vs previous clubs)
6. Historical xG / 90
7. Historical xA / 90
8. Historical goals / 90
9. Historical assists / 90
10. Match xG (raw vs difficulty-adjusted)
11. Match xA (raw vs difficulty-adjusted)
12. Model Rank vs FPL Consensus Rank

==================================================
4. EXPECTED-MINUTES DECOMPOSITION
==================================================

Inspect expected_minutes_v1 forAwoniyni and Osula:

- What inputs are being passed into expected_minutes_v1?
- How many relevant historical matches does the dataset contain for them?
- Are previous-club or non-EPL minutes included?
- Does the model observe current-club start role evidence?
- Does low-sample fallback kick in?
- What are the raw model outputs before calibration?
- What are the final calibrated outputs?
- Why did expected_minutes_v1 assign ~75–85 expected minutes?

==================================================
5. PER-90 EXTRAPOLATION AUDIT
==================================================

Audit how xG and xA are projected per match:

Formula currently used:
Match xG = xG_per_90 * (Expected_Minutes / 90) * Opponent_Factor

Determine:
1. What sample size is xG_per_90 calculated over?
2. Is there any Bayesian shrinkage / smoothing towards position priors?
3. If a player played 200 minutes and scored 2 goals (1.00 goal/90), does the system assume they maintain 1.00 goal/90 over 80 minutes?
4. What is the effective confidence interval around their per-90 rates?

==================================================
6. SENSITIVITY ANALYSIS
==================================================

For Awoniyi, Osula, Marmoush, and Beto, compute hypothetical xP under:

1. 30 Expected Minutes
2. 45 Expected Minutes
3. 60 Expected Minutes
4. 75 Expected Minutes
5. 90 Expected Minutes

Also compute xP if per-90 rates are shrunk towards position-average priors:
- Forward mean xG/90
- Midfielder mean xG/90

==================================================
7. MARKET VS MODEL COMPARISON — JOAO PEDRO & CALVERT-LEWIN
==================================================

Investigate why market consensus ranks João Pedro (#15) and Calvert-Lewin (#26) higher than our model:

- Are their per-90 rates lower than Awoniyi/Osula?
- Are their expected minutes lower?
- Is their team strength / opponent rating suppressing their projections?

==================================================
8. POINTS VS VALUE DIAGNOSTIC
==================================================

Evaluate whether these outliers remain attractive on a Points-Per-Million (PPM) basis:

- Awoniyi (£5.5m)
- Osula (£4.5m)
- Marmoush (£7.0m)
- Beto (£5.0m)

Determine if their high model rank is driven purely by raw xP or also by exceptional value efficiency.

==================================================
9. ROOT CAUSE CLASSIFICATION
==================================================

For Awoniyi, Osula, Marmoush, and Beto, classify the primary driver of their high projection into one of:

A. Legitimate Differential
B. Missing Injury / Availability Data
C. Expected-Minutes / Role Issue
D. High Per-90 Extrapolation Risk
E. Opponent Mapping Error
F. Data Scaling / Unit Error
G. Model Architecture Limitation
H. Tactical Role Misclassification
I. Price / Value Distortion

Provide empirical justification for each classification.

==================================================
10. REQUIRED DIAGNOSTIC ANSWERS
==================================================

Answer explicitly:

1. Is Awoniyi’s #3 ranking statistically justified by current data, or is it an artifact of low-sample per-90 extrapolation?
2. Is Osula’s #7 ranking driven by expected minutes, per-90 efficiency, or both?
3. Does expected_minutes_v1 require further refinement for squad-rotation strikers?
4. Does the per-90 rate engine require sample-size shrinkage for low-minute players?

==================================================
11. READ-ONLY FRONTEND INTEGRATION
==================================================

Add a diagnostic view to the frontend UI (`frontend/index.html`):

- Add a "ROLE & MINUTES AUDIT" section
- Clearly label it: "DIAGNOSTIC ONLY — DOES NOT AFFECT PROJECTIONS"
- Display expected minutes, P(start), P(60+), P(0), historical mins, xG/90, xA/90, model rank, market consensus rank, and risk classification.

==================================================
12. REGRESSION TESTING
==================================================

Add unit tests in `tests/test_phase3c6_expected_minutes_role_audit.py`:

- Verify production projections remain 100% unchanged
- Verify expected_minutes_v1 behavior is documented accurately
- Verify diagnostic shrinkage formulas run safely without NaN errors

==================================================
13. DOCUMENTATION & SUMMARY
==================================================

Produce:
1. `docs/prompts/PHASE_3C6_EXPECTED_MINUTES_ROLE_AUDIT.md`
2. `docs/phases/PHASE_3C6_EXPECTED_MINUTES_ROLE_AUDIT.md`
3. Update `docs/ROADMAP.md`

Present a full 31-point comprehensive report detailing all findings.

STOP after the report and wait for user review.
