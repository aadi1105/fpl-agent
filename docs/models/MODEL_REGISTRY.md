# Model Registry — FPL 2026/27 Decision Engine

This registry tracks all active baseline models and trained machine learning models across the system.

---

## 🟢 Currently Active Baseline Models (Production Engine)

| Model Name | Model Type | Implementation File | Status | Evaluation Metric / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **`minutes_v0_baseline`** | Deterministic Heuristic | [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py#L39) | **ACTIVE (PROD)** | Heuristic based on injury status, chance of playing, and price tiers |
| **`xg_xa_v0_baseline`** | Price-Tier Heuristic | [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py#L84) | **ACTIVE (PROD)** | Uses underlying per-90 metrics or price-tier defaults (`high`, `mid`, `low`) |
| **`team_ratings_v0`** | Deterministic / Bayesian | [`backend/projections/team_ratings.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/team_ratings.py) | **ACTIVE (PROD)** | xG/xGA per match shrunk toward 1000.0 baseline, clamped to $[600, 1600]$ |
| **`cs_prob_v0`** | Linear Ratio Scaling | [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py#L175) | **ACTIVE (PROD)** | $\text{CS}\% = \text{clamp}(0.32 \times \text{cs\_ratio}, 0.04, 0.75)$ |
| **`defcon_v0_poisson`** | Poisson Probability Model | [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py#L69) | **ACTIVE (PROD)** | $P(\text{CBIT} \ge 10 \mid \lambda = \text{cbit\_match})$ for 2026/27 DEFCON rules |

---

## 🟡 Trained Machine Learning Models (Evaluated & Backtested)

| Model Name | Target Variable | Algorithm | Status | Validation LogLoss / MAE | Test LogLoss / MAE | Beats Baseline? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`minutes_start_v1`** | $P(\text{start})$ | LightGBM Classifier | **TRAINED / EVALUATED** | `0.2816` LogLoss | `0.2568` LogLoss (ROC-AUC `0.9497`) | **YES** ($\uparrow 27.9\%$) |
| **`minutes_regression_v1`** | Expected Minutes | LightGBM Regressor | **TRAINED / EVALUATED** | `14.05` MAE | `12.84` MAE (RMSE `22.49`) | **YES** ($\uparrow 5.4\%$) |
| **`minutes_60plus_v1`** | $P(60+\text{ mins})$ | LightGBM Classifier | **TRAINED / EVALUATED** | `0.2871` LogLoss | `0.2609` LogLoss (ROC-AUC `0.9455`) | **YES** ($\uparrow 27.6\%$) |
| **`minutes_zero_v1`** | $P(0\text{ mins})$ | LightGBM Classifier | **TRAINED / EVALUATED** | `0.3142` LogLoss | `0.2838` LogLoss (PR-AUC `0.9654`) | **YES** ($\uparrow 31.3\%$) |

---

## 🔴 Planned Machine Learning Models (Future Phases)

| Model Name | Target Variable | Proposed Algorithm | Status | Required Benchmark to Beat |
| :--- | :--- | :--- | :--- | :--- |
| **`xg_v1_lgbm`** | Expected Goals ($xG$) per 90 | LightGBM Regressor | 🔴 **PLANNED** | Must beat `xg_xa_v0_baseline` out-of-sample |
| **`xa_v1_lgbm`** | Expected Assists ($xA$) per 90 | LightGBM Regressor | 🔴 **PLANNED** | Must beat `xg_xa_v0_baseline` out-of-sample |
| **`cs_v1_lgbm`** | Clean Sheet Probability ($CS\%$) | LightGBM Classifier | 🔴 **PLANNED** | Must beat `cs_prob_v0` out-of-sample |
| **`defcon_v1_lgbm`** | Defender DEFCON Probability | LightGBM Classifier | 🔴 **PLANNED** | Must beat `defcon_v0_poisson` Log-Loss |
