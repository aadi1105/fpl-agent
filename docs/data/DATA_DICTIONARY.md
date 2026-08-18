# Data Dictionary — Historical ML Dataset & Database Schemas

---

## 1. Historical ML Dataset Schema (`data/ml/historical_minutes_dataset.csv`)

The dataset contains **110,268 player-gameweek snapshot records** across four seasons (2022/23 – 2025/26).

### A. Identifiers
| Field Name | Data Type | Source | Description | Pre-Deadline? |
| :--- | :--- | :--- | :--- | :--- |
| `season` | `str` | Metadata | Season identifier (`2022-23`, `2023-24`, `2024-25`, `2025-26`) | Yes |
| `gameweek` | `int` | FPL GW | Gameweek number ($1 \dots 38$) | Yes |
| `player_id` | `int` | FPL API | Unique FPL element ID | Yes |
| `player_name` | `str` | FPL API | Web name or full name of player | Yes |
| `team` | `str` | FPL API | Player's club name | Yes |
| `position` | `str` | FPL API | Normalized position (`GKP`, `DEF`, `MID`, `FWD`) | Yes |

### B. Fixture & Team Strength Features
| Field Name | Data Type | Source | Description | Pre-Deadline? |
| :--- | :--- | :--- | :--- | :--- |
| `opponent` | `str` | Fixtures | Opponent club name | Yes |
| `opponent_id` | `int` | Fixtures | Opponent FPL team ID | Yes |
| `home_away` | `str` | Fixtures | `H` for Home match, `A` for Away match | Yes |
| `fixture_difficulty` | `float` | Computed | Estimated difficulty rating ($1.0 \dots 5.0$) | Yes |
| `team_attack_rating` | `float` | Team Ratings | Player team attacking rating ($600.0 \dots 1600.0$) | Yes |
| `team_defence_rating` | `float` | Team Ratings | Player team defensive rating ($600.0 \dots 1600.0$) | Yes |
| `opponent_attack_rating` | `float` | Team Ratings | Opponent team attacking rating ($600.0 \dots 1600.0$) | Yes |
| `opponent_defence_rating` | `float` | Team Ratings | Opponent team defensive rating ($600.0 \dots 1600.0$) | Yes |

### C. Recent Player Rolling Features (GW $< N$)
| Field Name | Data Type | Description | Pre-Deadline? |
| :--- | :--- | :--- | :--- |
| `minutes_last_1` | `int` | Minutes played in previous gameweek ($GW - 1$) | Yes |
| `minutes_last_3` | `int` | Sum of minutes played over last 3 gameweeks | Yes |
| `minutes_last_5` | `int` | Sum of minutes played over last 5 gameweeks | Yes |
| `minutes_last_10` | `int` | Sum of minutes played over last 10 gameweeks | Yes |
| `starts_last_1` | `int` | Started in previous gameweek (1 or 0) | Yes |
| `starts_last_3` | `int` | Total starts over last 3 gameweeks | Yes |
| `starts_last_5` | `int` | Total starts over last 5 gameweeks | Yes |
| `starts_last_10` | `int` | Total starts over last 10 gameweeks | Yes |
| `appearances_last_5` | `int` | Appearances ($>0$ mins) over last 5 gameweeks | Yes |
| `bench_appearances_last_5` | `int` | Substitute appearances over last 5 gameweeks | Yes |
| `unused_substitute_last_5` | `int` | Unused substitute appearances over last 5 gameweeks | Yes |
| `average_minutes_last_5` | `float` | Average minutes per match over last 5 gameweeks | Yes |
| `average_minutes_last_10` | `float` | Average minutes per match over last 10 gameweeks | Yes |

### D. Schedule & Context Features
| Field Name | Data Type | Description | Pre-Deadline? |
| :--- | :--- | :--- | :--- |
| `price` | `float` | Player cost in millions (e.g. £14.0m) | Yes |
| `days_since_last_match` | `float` | Rest days since team's last competitive match | Yes |
| `matches_in_previous_14_days` | `int` | Matches played by team in previous 14 days | Yes |
| `matches_in_previous_21_days` | `int` | Matches played by team in previous 21 days | Yes |
| `fixture_congestion` | `int` | 1 if $\ge 3$ matches in 14 days, else 0 | Yes |
| `injury_status` | `str` | Explicit missing status indicator (`unknown_historical`) | Yes |
| `feature_as_of` | `str` | Temporal snapshot identifier (`{season}_GW{gw}_pre_deadline`) | Yes |
| `split` | `str` | Data split assignment (`train`, `validation`, `test`) | Yes |

### E. Target Variables (Actual GW Outcome)
| Field Name | Data Type | Target? | Description |
| :--- | :--- | :--- | :--- |
| `target_started` | `int` | **TARGET** | 1 if player started in target GW, 0 otherwise |
| `target_minutes` | `int` | **TARGET** | Total actual minutes played in target GW |
| `target_60_plus` | `int` | **TARGET** | 1 if `target_minutes` $\ge 60$, 0 otherwise |
| `target_zero_minutes` | `int` | **TARGET** | 1 if `target_minutes` $== 0$, 0 otherwise |

---

## 2. Historical xG Dataset Schema (`data/ml/historical_xg_dataset.csv`)

The dataset contains **113,592 per-fixture snapshot records** across four seasons (2022/23 – 2025/26).

### A. Identifiers & Match Keys
| Field Name | Data Type | Description | Pre-Deadline? |
| :--- | :--- | :--- | :--- |
| `season` | `str` | Season identifier (`2022-23`, `2023-24`, `2024-25`, `2025-26`) | Yes |
| `gameweek` | `int` | Gameweek number ($1 \dots 38$) | Yes |
| `fixture_id` | `int` | Unique FPL match fixture ID | Yes |
| `player_id` | `int` | Unique FPL element ID | Yes |
| `player_name` | `str` | Web name or full name of player | Yes |
| `position` | `str` | Normalized position (`GKP`, `DEF`, `MID`, `FWD`) | Yes |

### B. Pre-Deadline Attacking Rolling Features (GW $< N$)
| Field Name | Data Type | Description | Pre-Deadline? |
| :--- | :--- | :--- | :--- |
| `expected_minutes_v1` | `float` | Production predicted expected minutes | Yes |
| `p_start` | `float` | Production predicted starting probability | Yes |
| `p_60_plus` | `float` | Production predicted 60+ minutes probability | Yes |
| `p_zero` | `float` | Production predicted zero minutes probability | Yes |
| `goals_last_1..10` | `float` | Rolling goals scored over prior match logs | Yes |
| `xg_last_1..10` | `float` | Rolling expected goals (Opta xG) over prior match logs | Yes |
| `threat_last_5..10` | `float` | Rolling ICT Threat metric over prior match logs | Yes |
| `creativity_last_5` | `float` | Rolling ICT Creativity metric over prior match logs | Yes |
| `goals_per_90_last_5` | `float` | Goals per 90 rate over prior 5 matches | Yes |
| `xg_per_90_last_5` | `float` | xG per 90 rate over prior 5 matches | Yes |

### C. Target Variable (Single Match Fixture)
| Field Name | Data Type | Target? | Description |
| :--- | :--- | :--- | :--- |
| `target_goals` | `int` | **TARGET** | Actual goals scored by player in this single match fixture |
| `actual_xg` | `float` | Reference | Actual Opta xG recorded in target fixture |

