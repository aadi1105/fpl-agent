# Phase 2B — Expected Minutes ML Model Evaluation Report

---

## 1. Objective
Train, evaluate, backtest, and compare machine learning models predicting player availability and expected minutes against deterministic heuristic baselines on `historical_minutes_dataset.csv`.

---

## 2. Chronological Split & Test Integrity

```text
TRAIN SET (48.7%):       2022/23 & 2023/24 (53,699 rows)
VALIDATION SET (24.7%):  2024/25 (27,231 rows) — Model Selection & Hyperparameter Tuning
TEST SET (26.6%):        2025/26 (29,338 rows) — Untouched single evaluation
```

---

## 3. Comparative Performance: ML vs. Baselines

### Model A: $P(\text{start})$ Binary Classification
* **Validation (2024/25)**: Baseline LogLoss `0.3713` $\to$ **LightGBM LogLoss `0.2816`** (**24.2% improvement**)
* **Test (2025/26)**: Baseline LogLoss `0.3561` $\to$ **LightGBM LogLoss `0.2568`** (**27.9% improvement**)
* **Test Metrics**: ROC-AUC = **`0.9497`**, Brier Score = **`0.0791`**, Calibration ECE = **`0.0117`** (Highly calibrated probability outputs).

### Model B: Expected Minutes Regression ($E[\text{minutes}]$)
* **Validation (2024/25)**: Baseline MAE `14.45 mins` $\to$ **LightGBM MAE `14.05 mins`**
* **Test (2025/26)**: Baseline MAE `13.58 mins` $\to$ **LightGBM MAE `12.84 mins`** (RMSE: `22.49` vs `26.04` baseline)
* **Subgroup Test MAE**:
  * Starters: `21.09 mins`
  * Substitutes: `9.60 mins`
  * Goalkeepers: `6.47 mins`
  * Defenders: `15.31 mins`
  * Midfielders: `12.87 mins`
  * Forwards: `12.07 mins`

### Model C: $P(60+ \text{ minutes})$ Binary Classification
* **Validation (2024/25)**: Baseline LogLoss `0.3778` $\to$ **LightGBM LogLoss `0.2871`**
* **Test (2025/26)**: Baseline LogLoss `0.3606` $\to$ **LightGBM LogLoss `0.2609`** (ROC-AUC: `0.9455`, ECE: `0.0077`)

### Model D: $P(0 \text{ minutes})$ Binary Classification
* **Validation (2024/25)**: Baseline LogLoss `0.4338` $\to$ **LightGBM LogLoss `0.3142`**
* **Test (2025/26)**: Baseline LogLoss `0.4132` $\to$ **LightGBM LogLoss `0.2838`** (PR-AUC: `0.9654`, ECE: `0.0125`)

---

## 4. Feature Importance (Top 10 Drivers)

1. `minutes_last_1` (553.0 gain)
2. `price` (452.0 gain)
3. `average_minutes_last_10` (390.0 gain)
4. `minutes_last_3` (350.0 gain)
5. `team_attack_rating` (342.0 gain)
6. `days_since_last_match` (330.0 gain)
7. `team_defence_rating` (216.0 gain)
8. `minutes_last_10` (216.0 gain)
9. `opponent_attack_rating` (180.0 gain)
10. `minutes_last_5` (151.0 gain)

---

## 5. Artifacts Created & Saved

* `models/minutes_start_v1.pkl`
* `models/minutes_regression_v1.pkl`
* `models/minutes_60plus_v1.pkl`
* `models/minutes_zero_v1.pkl`
* `models/phase2b_evaluation_report.json`

---

## 6. Live Engine Status & Deployment Recommendation

> [!NOTE]
> **CURRENT PRODUCTION STATUS**: Baselines remain active in live production engine (`backend/projections/engine.py`).
> **RECOMMENDATION**: ML models demonstrably beat baselines out-of-sample across all 4 metrics and are **RECOMMENDED FOR DEPLOYMENT**.

---

## 7. Result
**COMPLETED SUCCESSFULLY (EVALUATED & TESTED)**. Verified via [`tests/test_phase2b_models.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase2b_models.py) (31/31 tests passing).
