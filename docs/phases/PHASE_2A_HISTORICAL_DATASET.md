# Phase 2A — Historical Leak-Free ML Dataset Construction

---

## 1. Objective
Build a clean, historical, pre-deadline, leak-free dataset across four seasons (2022/23 to 2025/26) for training future expected-minutes and underlying performance machine learning models.

---

## 2. Dataset Construction Architecture

### Source Data & Processing
* Raw historical FPL match logs fetched from vaastav open-source repository and cached in `data/raw/`.
* Processed by [`backend/ml/dataset_builder.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/dataset_builder.py).
* Aggregated raw match logs to 1 pre-deadline snapshot per `(season, gameweek, player_id)` tuple.
* Total Rows: **110,268 records** across 1,475 unique players and 23 Premier League teams.

---

## 3. Time-Based Train / Validation / Test Split Plan

```text
TRAIN SPLIT (48.7%):       2022/23 (24,957 rows) + 2023/24 (28,742 rows) = 53,699 rows
VALIDATION SPLIT (24.7%):  2024/25 = 27,231 rows
TEST SPLIT (26.6%):        2025/26 = 29,338 rows
```

---

## 4. Key Quality & Temporal Isolation Controls

1. **GW1 Rolling Features**: In GW1, all prior rolling statistics (`minutes_last_1`, `starts_last_1`, `minutes_last_5`) are strictly $0$.
2. **Strict Pre-Deadline Isolation**: Features for GW $N$ use strictly match data from GW $< N$.
3. **Leak-Free Team Ratings**: Historical team ratings for GW $N$ use only matches played in GW $< N$ of that season.
4. **Target Variable Isolation**: `target_started`, `target_minutes`, `target_60_plus`, and `target_zero_minutes` are strictly separated from input features.

---

## 5. Manual Temporal Audits

### 1. Erling Haaland (2023/24 GW10)
* Snapshot: `2023-24_GW10_pre_deadline`
* Opponent: vs Brighton (A) | Opp Def Rating: `995.6`
* Rolling Prior Stats (GW $< 10$): `minutes_last_1`: 90 | `minutes_last_5`: 450 | `avg_mins_last_5`: 90.0
* Target Outcome (GW10): `target_minutes`: 90 | `target_started`: 1 | `target_60_plus`: 1

### 2. Bukayo Saka (2024/25 GW15)
* Snapshot: `2024-25_GW15_pre_deadline`
* Opponent: vs Man City (A) | Opp Def Rating: `1075.8`
* Rolling Prior Stats (GW $< 15$): `minutes_last_1`: 90 | `minutes_last_5`: 415 | `avg_mins_last_5`: 83.0
* Target Outcome (GW15): `target_minutes`: 90 | `target_started`: 1 | `target_60_plus`: 1

### 3. Gabriel Magalhães (2022/23 GW20)
* Snapshot: `2022-23_GW20_pre_deadline`
* Opponent: vs Leeds (A) | Opp Def Rating: `960.9`
* Rolling Prior Stats (GW $< 20$): `minutes_last_1`: 90 | `minutes_last_5`: 450 | `avg_mins_last_5`: 90.0
* Target Outcome (GW20): `target_minutes`: 90 | `target_started`: 1 | `target_60_plus`: 1

---

## 6. Result
**COMPLETED SUCCESSFULLY**. Verified via [`tests/test_phase2a_dataset.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase2a_dataset.py) (27/27 tests passing).

---

## 7. Development Prompt
Refer to [`docs/prompts/PHASE_2A_HISTORICAL_DATASET.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/prompts/PHASE_2A_HISTORICAL_DATASET.md).
