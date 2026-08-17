# Phase 1 Prompt: Baseline Fixture-Aware Projections & Optimizer

```text
FPL AI — PHASE 1: FIXTURE-AWARE GAMEWEEK PROJECTIONS & ARITHMETIC AUDIT

1. OBJECTIVE

The goal is to move from static season-level projections to dynamic, fixture-aware Gameweek projections (GW1 to GW8), and verify that our projections feed correctly into the OR-Tools Squad Optimizer.

We need to:
- Build fixture-aware projections for each player for upcoming gameweeks.
- Implement proper fixture difficulty scaling for attacking and defensive stats.
- Integrate DEFCON (Clearances, Blocks, Interceptions, Tackles) 2026/27 scoring rules.
- Expose an API endpoint for Gameweek-specific projection diagnostics.
- Ensure the Optimizer can optimize over a multi-gameweek horizon (e.g. GW1-GW4 weighted).
- Audit the projection arithmetic to ensure no NaN, zero-division, or ungrounded values.

2. FIXTURE DIFFICULTY & MODIFIERS

Attacking Modifier:
- Home factor: 1.05x, Away factor: 0.95x
- Fixture difficulty scale (1 to 5):
  - Difficulty 1 (Very Easy): 1.25x
  - Difficulty 2 (Easy): 1.10x
  - Difficulty 3 (Average): 1.00x
  - Difficulty 4 (Hard): 0.85x
  - Difficulty 5 (Very Hard): 0.70x

Clean Sheet Probability:
- Base CS probability by position tier and team strength.
- Multiplied by fixture factor:
  - Difficulty 1: 1.40x
  - Difficulty 2: 1.15x
  - Difficulty 3: 1.00x
  - Difficulty 4: 0.75x
  - Difficulty 5: 0.50x

3. 2026/27 DEFCON RULE MODELLING
Defenders gain +2 pts for reaching 10+ CBIT (Clearances, Blocks, Interceptions, Tackles) in a match.
Poisson model for P(CBIT >= 10 | lambda = cbit_per_match).

4. OPTIMIZER MULTI-GAMEWEEK HORIZON
Horizon weights: GW1: 55%, GW2: 20%, GW3: 15%, GW4: 10%.
```
