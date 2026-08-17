# Machine Learning Models Specifications & Evaluation

---

## 1. Phase 2B Expected Minutes ML Models (Trained & Evaluated)

### A. Model Overview
The Phase 2B availability models predict player starting probability $P(\text{start})$, expected minutes $E[\text{minutes}]$, $P(60+\text{ mins})$, and non-appearance probability $P(0\text{ mins})$ before an FPL deadline.

### B. Artifact Locations
* **`models/minutes_start_v1.pkl`** — LightGBM classifier for $P(\text{start})$
* **`models/minutes_regression_v1.pkl`** — LightGBM regressor for $E[\text{minutes}]$
* **`models/minutes_60plus_v1.pkl`** — LightGBM classifier for $P(60+)$
* **`models/minutes_zero_v1.pkl`** — LightGBM classifier for $P(0)$
* **`models/phase2b_evaluation_report.json`** — Comprehensive metrics report

### C. Out-of-Sample Performance Summary (2025/26 Test Set)

| Target | Baseline Metric | LightGBM ML Metric | Out-of-Sample Improvement | Status |
| :--- | :--- | :--- | :--- | :--- |
| **$P(\text{start})$** | `0.3561` LogLoss | **`0.2568` LogLoss** | **27.9% improvement** | **Trained / Evaluated** |
| **$E[\text{minutes}]$** | `13.58` MAE | **`12.84` MAE** (RMSE `22.49` vs `26.04`) | **5.4% improvement** | **Trained / Evaluated** |
| **$P(60+)$** | `0.3606` LogLoss | **`0.2609` LogLoss** | **27.6% improvement** | **Trained / Evaluated** |
| **$P(0)$** | `0.4132` LogLoss | **`0.2838` LogLoss** | **31.3% improvement** | **Trained / Evaluated** |

---

## 2. Planned Future ML Models (NOT YET IMPLEMENTED)

* **`xg_v1_lgbm`**: Expected Goals ($xG$) per 90 (Phase 3)
* **`xa_v1_lgbm`**: Expected Assists ($xA$) per 90 (Phase 3)
* **`cs_v1_lgbm`**: Clean Sheet Probability ($CS\%$) (Phase 4)
* **`defcon_v1_lgbm`**: Defender DEFCON Probability (Phase 4)
