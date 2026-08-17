# Phase 2A Prompt: Historical ML Dataset Construction

```text
FPL AI — PHASE 2A: HISTORICAL DATASET CONSTRUCTION

OBJECTIVE:
Build a clean, historical, pre-deadline, leak-free dataset across seasons 2022/23 to 2025/26 that can later be used to train expected-minutes and statistical ML models.

CRITICAL TEMPORAL RULE:
For PLAYER X — GW N, ALL features must represent information available BEFORE the GW N deadline.
The target represents what actually happened DURING GW N.

FEATURES INCLUDED:
1. Identifiers: season, gameweek, player_id, player_name, team, position
2. Fixture: opponent, home_away, fixture_difficulty, team_attack_rating, team_defence_rating, opponent_attack_rating, opponent_defence_rating
3. Recent Player Features: minutes_last_1/3/5/10, starts_last_1/3/5/10, appearances_last_5, bench_appearances_last_5, unused_substitute_last_5, average_minutes_last_5/10
4. Player Status: price, position, team, injury_status (explicit missing indicator)
5. Schedule / Context: days_since_last_match, matches_in_previous_14_days, matches_in_previous_21_days, fixture_congestion
6. Targets: target_started, target_minutes, target_60_plus, target_zero_minutes

LEAKAGE PREVENTION & SPLIT:
- Chronological time-based split: TRAIN (2022/23 & 2023/24), VALIDATION (2024/25), TEST (2025/26).
- Zero GW N or future match data in GW N rolling features.
- Zero ML model training during Phase 2A.
```
