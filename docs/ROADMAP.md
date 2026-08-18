# Authoritative Roadmap — FPL 2026/27 Decision Engine

---

## 📅 Status Overview

| Phase | Description | Status | Completion Date |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Baseline Projection Engine & MILP Optimizer | **COMPLETED** | August 2026 |
| **Phase 1A** | Fixture-Aware Gameweek Projections & UI | **COMPLETED** | August 2026 |
| **Phase 1B** | Projection Component Sanity Audit | **COMPLETED** | August 2026 |
| **Phase 1C** | Team Strength & Fixture Context Layer | **COMPLETED** | August 2026 |
| **Phase 2A** | Historical Leak-Free ML Dataset Construction | **COMPLETED** | August 2026 |
| **Phase 2B** | Expected Minutes ML Models ($P(\text{start})$, $E[\text{mins}]$, $P(60+)$, $P(0)$) | **COMPLETED (EVALUATED)** | August 2026 |
| **Phase 2C** | Expected Minutes Validation & Production Integration | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3A** | Expected Goals ($xG$) ML Model (`xg_v1_lgbm`) | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3B** | Expected Assists ($xA$) ML Model | 🔴 **PLANNED** | Future |
| **Phase 4** | Clean Sheet & DEFCON ML Models | 🔴 **PLANNED** | Future |
| **Phase 5** | Model Ensemble & Uncertainty Quantification | 🔴 **PLANNED** | Future |
| **Phase 6** | News, RAG & Manager Presser Agent | 🔴 **PLANNED** | Future |
| **Phase 7** | Mini-League Game Theory & Ownership Optimization | 🔴 **PLANNED** | Future |

---

## 📑 Completed Phases Detail

### Phase 3A: Expected Goals ($xG$) Machine Learning Model
* Constructed leak-free per-fixture historical xG dataset (`data/ml/historical_xg_dataset.csv`) across 113,592 records (2022-2026).
* Evaluated LightGBM Poisson, Tweedie, and L2 Regression on 2024/25 Validation Set.
* Selected Poisson LightGBM (`xg_v1_lgbm`) and evaluated on untouched 2025/26 Test Set:
  - **Poisson Deviance**: Baseline `0.1805` $\to$ ML **`0.1622`** (+10.15% improvement).
  - **MAE**: Baseline `0.0692` goals $\to$ ML **`0.0619`** goals (+10.55% improvement).
  - **RMSE**: Baseline `0.1904` $\to$ ML **`0.1880`** (+1.24% improvement).
* Built production inference wrapper [`backend/ml/xg_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/xg_predictor.py) with automatic fallback to `xg_baseline_v1`.
* Integrated into [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py) and exposed diagnostic fields (`xg_baseline`, `xg_ml`, `xg_model_version`, `used_xg_fallback`).
* Complete details in [`docs/phases/PHASE_3A_EXPECTED_GOALS.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/phases/PHASE_3A_EXPECTED_GOALS.md).
* Full pytest test suite passing (39/39 tests).

### Phase 2C: Expected Minutes Validation & Production Integration
* Verified 0% temporal leakage on 2025/26 test set.
* Built production inference wrapper [`backend/ml/minutes_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/minutes_predictor.py) with automatic fallback to deterministic baseline (`expected_minutes_baseline_v1`).
* Integrated `expected_minutes_v1` into [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py) without double-counting.
* Updated API diagnostics endpoint to output `expected_minutes_baseline`, `expected_minutes_ml`, `model_version`, `p_start`, `p_60_plus`, `p_zero`, `used_fallback`.
* Full test suite passing (35/35 tests).
