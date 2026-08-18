# Model Registry — FPL 2026/27 Decision Engine

This registry tracks all active production models, fallback baselines, and planned machine learning models across the system.

---

## 🟢 Currently Active Production Models (Production Engine)

| Model Name | Model Type | Implementation File | Status | Evaluation Metric / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`expected_minutes_v1`** | LightGBM ML Classifier & Regressor | [`backend/ml/minutes_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/minutes_predictor.py) | **ACTIVE (PROD)** | Predicts $xMins$, $P(\text{start})$, $P(60+)$, $P(0)$. Out-of-sample MAE `12.84` mins |
| **`xg_v1_lgbm`** | LightGBM Poisson Regressor | [`backend/ml/xg_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/xg_predictor.py) | **ACTIVE (PROD)** | Predicts fixture $xG$. Out-of-sample Poisson Dev `0.1622` (+10.15% over baseline) |
| **`xa_v1_lgbm`** | LightGBM Poisson Regressor | [`backend/ml/xa_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/xa_predictor.py) | **ACTIVE (PROD)** | Predicts fixture $xA$. Out-of-sample Poisson Dev `0.1737` (+8.05% over baseline) |
| **`team_ratings_v0`** | Deterministic / Bayesian | [`backend/projections/team_ratings.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/team_ratings.py) | **ACTIVE (PROD)** | xG/xGA per match shrunk toward 1000.0 baseline, clamped to $[600, 1600]$ |
| **`cs_prob_v0`** | Linear Ratio Scaling | [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py#L175) | **ACTIVE (PROD)** | $\text{CS}\% = \text{clamp}(0.32 \times \text{cs\_ratio}, 0.04, 0.75)$ |
| **`defcon_v0_poisson`** | Poisson Probability Model | [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py#L69) | **ACTIVE (PROD)** | $P(\text{CBIT} \ge 10 \mid \lambda = \text{cbit\_match})$ for 2026/27 DEFCON rules |

---

## 🟡 Fallback & Reference Baseline Models

| Model Name | Model Type | Implementation File | Status | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`expected_minutes_baseline_v1`** | Deterministic Heuristic | [`backend/ml/minutes_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/minutes_predictor.py#L52) | **FALLBACK (PROD)** | Safe production fallback if minutes ML model artifact fails |
| **`xg_baseline_v1`** | Deterministic Price-Tier Heuristic | [`backend/ml/xg_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/xg_predictor.py#L53) | **FALLBACK (PROD)** | Safe production fallback if xG ML model artifact fails |
| **`xa_baseline_v1`** | Deterministic Price-Tier Heuristic | [`backend/ml/xa_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/xa_predictor.py#L48) | **FALLBACK (PROD)** | Safe production fallback if xA ML model artifact fails |

---

## 🔴 Planned Machine Learning Models (Future Phases)

| Model Name | Target Variable | Proposed Algorithm | Status | Required Benchmark to Beat |
| :--- | :--- | :--- | :--- | :--- |
| **`xa_v1_lgbm`** | Expected Assists ($xA$) per 90 | LightGBM Regressor | 🔴 **PLANNED** | Must beat baseline out-of-sample |
| **`cs_v1_lgbm`** | Clean Sheet Probability ($CS\%$) | LightGBM Classifier | 🔴 **PLANNED** | Must beat `cs_prob_v0` out-of-sample |
| **`defcon_v1_lgbm`** | Defender DEFCON Probability | LightGBM Classifier | 🔴 **PLANNED** | Must beat `defcon_v0_poisson` Log-Loss |
