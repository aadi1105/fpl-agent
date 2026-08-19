# PHASE 3C.7 — TEMPORAL / RECENCY & CURRENT-FORM AUDIT

We are continuing from Phase 3C.6.

Phase 3C.6 identified two important weaknesses:

1. Low-sample players can receive excessive expected minutes because synthetic recent-start features can create false evidence of a starting role.

2. Low-sample xG/xA rates can be extrapolated too confidently without sufficient uncertainty/shrinkage.

Phase 3C.6 also revealed a broader modelling question:

Our current system relies heavily on historical player performance, but FPL prediction is fundamentally a forward-looking problem.

A player's long-term ability is not necessarily the same as their current ability.

Examples:

- A player may have excellent historical xG/90 but poor recent form and an uncertain current role.
- A player may have mediocre historical numbers but have substantially improved in a new team, role, or tactical system.
- A player may retain strong underlying ability but currently be unlikely to start.
- A player's historical statistics may come from a previous club and therefore describe ability better than current role.

The goal of this phase is NOT to change the production models.

The goal is to determine empirically whether recent/temporal information improves prediction of FUTURE performance.

==================================================
0. ABSOLUTE NO-CHANGE RULE
==================================================

This is a READ-ONLY research and backtesting phase.

Do NOT modify:

- expected_minutes_v1
- xG model
- xA model
- clean-sheet model
- DEFCON model
- scoring engine
- optimizer
- optimizer objectives
- production projections
- deployed model artifacts

Do NOT add recency weighting to production.

Do NOT manually alter any player's projection.

Do NOT use current 2026/27 information to train historical models.

Do NOT use future information.

Do NOT use post-deadline information.

The purpose is to determine whether temporal features have predictive value BEFORE implementing them.

==================================================
1. CORE RESEARCH QUESTION
==================================================

Answer this question:

"Does recent information improve out-of-sample prediction of future player performance compared with our current historical baseline?"

Test this separately for:

A. Expected Minutes
B. xG
C. xA

Do not assume the answer is YES.

==================================================
2. TEMPORAL DATASET DESIGN
==================================================

Construct a chronological walk-forward dataset (2022/23 – 2025/26) strictly using features available before deadline GW N.

==================================================
3. TEMPORAL FEATURE FAMILIES
==================================================

Construct feature families across multiple recency windows:
- Attacking Form: xG/90 (last 3, 5, 10, season, career), xA/90 (last 3, 5, 10, season, career)
- Raw Attacking Volume: xG, xA, threat, shots
- Minutes/Role: minutes (last 3, 5, 10), starts (last 3, 5, 10), current-club minutes/starts

==================================================
4. CASE STUDIES & DIAGNOSTICS
==================================================

Evaluate:
- Marmoush
- Calvert-Lewin
- Awoniyi
- Osula
- Beto
- Sample-size interaction (<300, 300-600, 600-1000, 1000-2000, 2000+)
- Transferred players
- Goals vs process stats
- Form regression to mean

==================================================
5. FRONTEND & DOCUMENTATION
==================================================

- Add read-only diagnostic card in `frontend/index.html`
- Create `docs/prompts/PHASE_3C7_TEMPORAL_RECENCY_AUDIT.md`
- Create `docs/phases/PHASE_3C7_TEMPORAL_RECENCY_AUDIT.md`
- Update `docs/ROADMAP.md`
- Present 25-point report and STOP for review.
