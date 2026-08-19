# PHASE 3C.8 — LOW-SAMPLE MINUTES & PER-90 SHRINKAGE IMPLEMENTATION

We are continuing from Phase 3C.6 and Phase 3C.7.

Phase 3C.6 identified two foundational weaknesses:

1. Low-sample players can receive artificially high expected minutes because synthetic recent-start features can create false evidence of a starting role.

2. Low-sample xG/xA rates can be extrapolated too confidently without sufficient uncertainty/shrinkage.

Phase 3C.7 then empirically demonstrated that temporal information improves future prediction:

- Expected Minutes: 41.24% MAE improvement
- xG: 38.39% MAE improvement
- xA: 23.56% MAE improvement

It also found:

- Minutes benefit most from recent starts/minutes, particularly recent 3–5 match windows.
- xG benefits from multi-window temporal information combined with a historical prior.
- xA benefits from longer recent windows combined with a historical prior.
- Very small samples require substantially more shrinkage.
- Extreme short-term xG/90 spikes regress strongly toward the player's prior.

The purpose of Phase 3C.8 is to IMPLEMENT AND VALIDATE the two foundational fixes identified by those audits:

A. Low-sample / current-role handling for Expected Minutes.

B. Sample-size-aware shrinkage for xG and xA.

This is still NOT the full production retraining/deployment phase.

==================================================
0. ABSOLUTE SCOPE
==================================================

Implement the methodology changes required by the Phase 3C.6 and 3C.7 findings.

Do NOT yet perform the full production deployment/retraining pipeline.

Do NOT modify the optimizer or optimizer objectives.

==================================================
1. PRESERVE CURRENT MODELS AS BASELINES
==================================================

Freeze v1 artifacts as baselines. Create versioned candidate models (`expected_minutes_candidate_v2`, `xg_candidate_v2`, `xa_candidate_v2`) clearly marked `CANDIDATE — NOT PRODUCTION`.

==================================================
2. FIX EXPECTED MINUTES — LOW-SAMPLE HANDLING
==================================================

Use actual fixture-level records. Do not infer synthetic starts from total minutes. Handle transfers and current-club evidence correctly.

==================================================
3. CURRENT-CLUB ROLE PRIOR & BAYESIAN SHRINKAGE
==================================================

Distinguish strong, weak, and no current-club evidence. Shrink toward position/price priors.

==================================================
4. xG & xA SAMPLE-SIZE SHRINKAGE
==================================================

Empirical Bayes shrinkage:
- $w_{xG}(N) = N / (N + 750)$
- $w_{xA}(N) = N / (N + 600)$
- Position priors learned from training data.

==================================================
5. FRONTEND & DOCUMENTATION
==================================================

- Add read-only comparison panel in `frontend/index.html`
- Create `docs/prompts/PHASE_3C8_LOW_SAMPLE_SHRINKAGE_IMPLEMENTATION.md`
- Create `docs/phases/PHASE_3C8_LOW_SAMPLE_SHRINKAGE_IMPLEMENTATION.md`
- Update `docs/ROADMAP.md`
- Present 25-point report and STOP for review.
