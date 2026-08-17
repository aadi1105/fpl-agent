# Phase 1C Prompt: Team Strength & Fixture Context Layer

```text
FPL AI — PHASE 1C: PROPER TEAM STRENGTH RATINGS

OBJECTIVE:
Create reliable team-level attacking and defensive strength ratings that can be used by the existing fixture-aware projection engine.
System must distinguish between strong/average/weak attacking & defensive teams.

TEAM RATINGS REQUIRED:
For every Premier League team:
1. Attacking Strength
2. Defensive Strength
Maintain Home Attacking, Away Attacking, Home Defensive, Away Defensive ratings.

RATING METHODOLOGY:
Baseline league average = 1000.0.
Clamped to [600.0, 1600.0].
Higher Defensive Rating = BETTER defence (concedes lower xGA).
Bayesian shrinkage for small sample sizes toward 1000.0 baseline.

FIXTURE PROJECTION INTEGRATION:
Integrate team ratings into the existing projection engine without double-counting.
att_multiplier = clamp(1000.0 / opp_def_rating * home_factor, 0.60, 1.50)
cs_ratio = clamp(team_def_rating / opp_att_rating * home_factor, 0.40, 2.50)

REQUIRES:
- 100% test coverage for team ratings & bounds.
- Diagnostic API endpoint exposing team ratings & modifiers.
- Zero ML training, zero optimizer modifications.
```
