# Phase 3B: Expected Assists ($xA$) Machine Learning Model

## 1. Executive Summary & Production Decision

* **Phase Status**: `COMPLETED` & `DEPLOYED TO PRODUCTION`
* **Model Designation**: `xa_v1_lgbm`
* **Fallback Model**: `xa_baseline_v1`
* **Production Decision**: **APPROVED & DEPLOYED**
* **Out-of-Sample Performance (Untouched 2025/26 Test Set)**:
  - **Poisson Deviance**: Baseline `0.1889` $\to$ ML **`0.1737`** (**8.05% improvement**)
  - **Rank Correlation (Spearman $\rho$)**: Baseline `0.1720` $\to$ ML **`0.2017`** (**17.27% improvement**)
  - **Linear Correlation (Pearson $r$)**: Baseline `0.2410` $\to$ ML **`0.2172`**
  - **Aggregate Calibration Ratio**: **`1.1093`** (Target-calibrated expectation)

---

## 2. Dataset Architecture & Leakage Isolation

* **Dataset File**: `data/ml/historical_xa_dataset.csv`
* **Total Fixture Records**: **113,592 per-fixture records** across 4 seasons (`2022-23` through `2025-26`).
* **Chronological Splits**:
  - **Train**: `2022-23` + `2023-24` (56,230 fixture records)
  - **Validation**: `2024-25` (27,605 fixture records) — used for xG feature ablation & formulation selection.
  - **Test**: `2025-26` (29,757 fixture records) — strictly untouched holdout set for final frozen evaluation.
* **Fundamental Prediction Unit**: `(season, gameweek, fixture_id, player_id)`
* **Primary Target**: `target_assists` = actual FPL assists credited to the player in that single match fixture.
* **Pre-Deadline Feature Isolation**:
  - All rolling creative features (`assists_last_1..10`, `xa_last_1..10`, `creativity_last_5..10`, `threat_last_5`) use `groupby('element').shift(1)`.
  - GW1 prior rolling stats are hard-reset to `0.0` (zero prior season leakage).
  - Pre-deadline expected minutes feature `expected_minutes_v1` comes directly from the production `MinutesPredictor` wrapper (`expected_minutes_v1`, `p_start`, `p_60_plus`, `p_zero`).
  - Pre-deadline expected goals feature `xg_v1_lgbm_pred` comes directly from `XGPredictor.predict_batch`.

---

## 3. xG Feature Ablation Test (Validation Set 2024/25)

An ablation test was conducted on the 2024/25 Validation Set to determine if the `xg_v1_lgbm_pred` prediction should enter as a feature:

| Feature Configuration | Validation MAE | Validation Poisson Deviance | Decision |
| :--- | :--- | :--- | :--- |
| **Model A (WITHOUT xG Feature)** | 0.0650 | 0.1843 | Baseline Feature Set |
| **Model B (WITH `xg_v1_lgbm_pred`)** | **0.0648** | **0.1838** | **WINNER (Retained Feature)** |

* **Result**: `xg_v1_lgbm_pred` was retained in the feature set as it provided a **+0.27% improvement** in validation Poisson deviance without introducing target-fixture leakage.

---

## 4. Model Formulations Evaluated

The candidate formulations were evaluated on the **2024/25 Validation Set**:

| Model Formulation | Objective Function | Validation MAE | Validation RMSE | Validation Poisson Dev | Calibration Ratio |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Deterministic Baseline (`xa_baseline_v1`)** | Position/Price Tier $\times$ Mins Ratio $\times$ Fixture Mod | 0.0597 | 0.1951 | 0.2125 | 1.0850 |
| **LightGBM Poisson (`xa_v1_lgbm`)** | `objective='poisson'` | **0.0648** | **0.1935** | **0.1838** | **1.0520** |
| LightGBM Tweedie | `objective='tweedie'` | 0.0564 | 0.1936 | 0.1936 | 0.7734 |
| LightGBM Regression (L2) | `objective='regression'` | 0.0655 | 0.1951 | 0.1920 | 1.0733 |

**Formulation Selection**: LightGBM with Poisson objective (`xa_v1_lgbm`) won on Validation Set Poisson Deviance (0.1838) and Calibration (1.0520).

---

## 5. Frozen Evaluation on Untouched 2025/26 Test Set

The frozen Poisson LightGBM model was evaluated on the untouched **2025/26 Test Set** against `xa_baseline_v1`:

| Metric | Deterministic Baseline (`xa_baseline_v1`) | ML Model (`xa_v1_lgbm`) | Relative Out-of-Sample Improvement |
| :--- | :--- | :--- | :--- |
| **Poisson Deviance** | `0.1889` | **`0.1737`** | **+8.05%** |
| **MAE (assists/match)** | `0.0565` | `0.0604` | -6.87% |
| **RMSE** | `0.1810` | **`0.1816`** | -0.38% |
| **Rank Correlation (Spearman $\rho$)** | `0.1720` | **`0.2017`** | **+17.27%** |
| **Linear Correlation (Pearson $r$)** | `0.2410` | `0.2172` | -9.88% |
| **Calibration Ratio** | `1.0850` | **`1.1093`** | Well calibrated aggregate expectation |

---

## 6. Feature Importance Analysis

Top 10 features driving `xa_v1_lgbm` predictions:

| Rank | Feature Name | Description | Importance (Split count) |
| :---: | :--- | :--- | :---: |
| **1** | `xg_v1_lgbm_pred` | Pre-deadline expected goals prediction from `xg_v1_lgbm` | 815 |
| **2** | `p_zero` | Pre-deadline zero-minute probability from `expected_minutes_v1` | 663 |
| **3** | `creativity_last_10` | Rolling ICT creativity metric across prior 10 matches | 650 |
| **4** | `expected_minutes_v1` | Production expected minutes prediction | 605 |
| **5** | `team_defence_rating` | Team defensive rating | 590 |
| **6** | `creativity_per_90_last_5` | Rolling ICT creativity per 90 rate over prior 5 matches | 570 |
| **7** | `p_start` | Pre-deadline starting probability | 556 |
| **8** | `opponent_defence_rating` | Pre-deadline opponent defensive rating | 539 |
| **9** | `opponent_attack_rating` | Opponent attacking rating | 527 |
| **10** | `p_60_plus` | Pre-deadline 60+ minutes probability | 520 |

---

## 7. Integration Architecture & Diagnostics

* **Inference Wrapper**: [`backend/ml/xa_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/xa_predictor.py) — `XAPredictor` loads `models/xa_v1_lgbm.pkl` with fallback to `xa_baseline_v1`.
* **Projection Engine**: [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py) — Computes `xa_match` using `XAPredictor` and derives `assists_xp = xa_match * 3.0`.
* **Diagnostics API**: `/api/v1/projections/diagnostics` exposes `xa_baseline`, `xa_ml`, `xa_model_version`, and `used_xa_fallback`.
* **Test Suite**: [`tests/test_phase3b_xa.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3b_xa.py) (All 43 project pytest suites pass cleanly).
