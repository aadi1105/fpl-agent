# Phase 3A: Expected Goals ($xG$) Machine Learning Model

## 1. Executive Summary & Production Decision

* **Phase Status**: `COMPLETED` & `DEPLOYED TO PRODUCTION`
* **Model Designation**: `xg_v1_lgbm`
* **Fallback Model**: `xg_baseline_v1`
* **Production Decision**: **APPROVED & DEPLOYED**
* **Out-of-Sample Performance**:
  - **Poisson Deviance**: Baseline `0.1805` $\to$ ML **`0.1622`** (**10.15% improvement**)
  - **Mean Absolute Error (MAE)**: Baseline `0.0692` goals $\to$ ML **`0.0619`** goals (**10.55% improvement**)
  - **Root Mean Squared Error (RMSE)**: Baseline `0.1904` $\to$ ML **`0.1880`** (**1.24% improvement**)
  - **Calibration Ratio**: **`1.13`** (Target-calibrated aggregate expectation)

---

## 2. Dataset Architecture & Leakage Isolation

* **Dataset File**: `data/ml/historical_xg_dataset.csv`
* **Total Fixture Records**: **113,592 per-fixture records** across 4 seasons (`2022-23` through `2025-26`).
* **Chronological Splits**:
  - **Train**: `2022-23` + `2023-24` (56,230 fixture records)
  - **Validation**: `2024-25` (27,605 fixture records) — used for formulation selection & hyperparameter tuning.
  - **Test**: `2025-26` (29,757 fixture records) — strictly untouched holdout set for final frozen evaluation.
* **Fundamental Prediction Unit**: `(season, gameweek, fixture_id, player_id)`
* **Primary Target**: `target_goals` = actual goals scored in that individual match fixture.
* **Pre-Deadline Feature Isolation**:
  - All rolling attacking features (`goals_last_1..10`, `xg_last_1..10`, `threat_last_5..10`, `creativity_last_5`) use `groupby('element').shift(1)`.
  - GW1 prior rolling stats are hard-reset to `0.0` (zero prior season leakage).
  - Pre-deadline expected minutes feature `expected_minutes_v1` comes directly from the production `MinutesPredictor` wrapper (`expected_minutes_v1`, `p_start`, `p_60_plus`, `p_zero`).

---

## 3. Model Formulations Evaluated

The candidate formulations were evaluated on the **2024/25 Validation Set**:

| Model Formulation | Objective Function | Validation MAE | Validation RMSE | Validation Poisson Dev | Calibration Ratio |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Deterministic Baseline (`xg_baseline_v1`)** | Price Tier $\times$ Mins Ratio $\times$ Fixture Mod | 0.0736 | 0.2026 | 0.1972 | 1.0520 |
| **LightGBM Poisson** | `objective='poisson'` | **0.0669** | **0.1998** | **0.1753** | **1.0267** |
| LightGBM Tweedie | `objective='tweedie'` | 0.0595 | 0.2004 | 0.1833 | 0.7965 |
| LightGBM Regression (L2) | `objective='regression'` | 0.0677 | 0.2015 | 0.1882 | 1.0454 |

**Formulation Selection**: LightGBM with Poisson objective (`xg_v1_lgbm`) won on Validation Set Poisson Deviance (0.1753) and Calibration (1.0267).

---

## 4. Frozen Evaluation on Untouched 2025/26 Test Set

The frozen Poisson LightGBM model was evaluated on the untouched **2025/26 Test Set** against `xg_baseline_v1`:

| Metric | Deterministic Baseline (`xg_baseline_v1`) | ML Model (`xg_v1_lgbm`) | Relative Out-of-Sample Improvement |
| :--- | :--- | :--- | :--- |
| **Poisson Deviance** | `0.1805` | **`0.1622`** | **+10.15%** |
| **MAE (goals/match)** | `0.0692` | **`0.0619`** | **+10.55%** |
| **RMSE** | `0.1904` | **`0.1880`** | **+1.24%** |
| **Rank Correlation (Spearman)** | `0.1850` | **`0.2307`** | **+24.70%** |
| **Linear Correlation (Pearson)** | `0.2610` | **`0.3286`** | **+25.90%** |

---

## 5. Feature Importance Analysis

Top 10 features driving `xg_v1_lgbm` predictions:

| Rank | Feature Name | Description | Importance (Split count) |
| :---: | :--- | :--- | :---: |
| **1** | `p_zero` | Pre-deadline zero-minute probability from `expected_minutes_v1` | 868 |
| **2** | `opponent_defence_rating` | Pre-deadline opponent defensive rating | 711 |
| **3** | `team_defence_rating` | Team defensive rating | 644 |
| **4** | `team_attack_rating` | Team attacking strength rating | 638 |
| **5** | `creativity_last_5` | Rolling ICT creativity metric across prior 5 matches | 608 |
| **6** | `expected_minutes_v1` | Production expected minutes prediction | 598 |
| **7** | `price` | Player price tier | 569 |
| **8** | `p_start` | Pre-deadline starting probability | 548 |
| **9** | `p_60_plus` | Pre-deadline 60+ minutes probability | 530 |
| **10** | `threat_last_10` | Rolling ICT threat metric across prior 10 matches | 522 |

---

## 6. Integration Architecture & Diagnostics

* **Inference Wrapper**: [`backend/ml/xg_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/xg_predictor.py) — `XGPredictor` loads `models/xg_v1_lgbm.pkl` with fallback to `xg_baseline_v1`.
* **Projection Engine**: [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py) — Computes `xg_match` using `XGPredictor` and derives `goals_xp = xg_match * goal_val`.
* **Diagnostics API**: `/api/v1/projections/diagnostics` exposes `xg_baseline`, `xg_ml`, `xg_model_version`, and `used_xg_fallback`.
* **Test Suite**: [`tests/test_phase3a_xg.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3a_xg.py) (All 39 project pytest suites pass cleanly).
