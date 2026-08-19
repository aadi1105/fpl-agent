# Phase 3C.8 — Low-Sample Minutes & Per-90 Shrinkage Implementation

> [!IMPORTANT]
> **CANDIDATE IMPLEMENTATION & OUT-OF-SAMPLE VALIDATION PHASE**
> This phase implemented and validated the Candidate V2 statistical foundation architecture for Expected Minutes (`expected_minutes_candidate_v2`), $xG$ (`xg_candidate_v2`), and $xA$ (`xa_candidate_v2`). All production v1 artifacts (`models/minutes_start_v1.pkl`, `models/xg_v1_lgbm.pkl`, `models/xa_v1_lgbm.pkl`), optimizer objectives, and scoring engines remain **100% unmodified**.

---

## 1. Problem Summary & Fix Methodology

### Expected Minutes Fix
- **Root Cause**: Previous feature imputation set synthetic `starts_last_5 = min(5.0, tot_mins / 80.0)`, treating small career minute totals (e.g. 240 mins) as 5 genuine starting appearances.
- **Candidate V2 Solution**: Requires actual fixture-level starting records. Implements Empirical Bayes evidence weighting $w_{\text{evidence}} = \min(1.0, \frac{\text{starts}_{\text{current\_club}}}{5.0})$ which shrinks sparse current-club evidence toward position/price priors.

### xG & xA Rate Shrinkage
- **Methodology**: Applied Empirical Bayes shrinkage based on historical sample size $N$ (mins):
  $$\text{xG90}_{\text{shrunk}} = w_{xG}(N) \cdot \text{xG90}_{\text{multi-window}} + (1 - w_{xG}(N)) \cdot Prior_{xG,pos} \quad \left(w_{xG} = \frac{N}{N + 750}\right)$$
  $$\text{xA90}_{\text{shrunk}} = w_{xA}(N) \cdot \text{xA90}_{\text{multi-window}} + (1 - w_{xA}(N)) \cdot Prior_{xA,pos} \quad \left(w_{xA} = \frac{N}{N + 600}\right)$$
- **Priors Learned from 2022-25 Data**:
  - $xG$ Priors: Forward = `0.380`, Midfielder = `0.220`, Defender = `0.060`.
  - $xA$ Priors: Forward = `0.140`, Midfielder = `0.180`, Defender = `0.090`.

---

## 2. Out-of-Sample Evaluation Results (2025/26 Test Set)

| Metric | V1 Production Baseline | Candidate V2 Implementation | Out-of-Sample Gain |
|---|---|---|---|
| **Expected Minutes MAE** | 56.70 mins | **38.17 mins** | **+32.68% MAE Gain** |
| **Expected Minutes RMSE** | 66.67 | **40.88** | **+38.69% RMSE Gain** |
| **$P(\text{start})$ Brier Score** | 0.5244 | **0.2707** | **+48.38% Brier Score Gain** |
| **Match $xG$ Deviance** | 0.2377 | **0.1734** | **+27.06% Deviance Gain** |
| **Match $xG$ MAE** | 0.1181 | **0.0861** | **+27.13% MAE Gain** |
| **Match $xA$ Deviance** | 0.1330 | **0.1076** | **+19.13% Deviance Gain** |
| **Match $xA$ MAE** | 0.0693 | **0.0555** | **+19.93% MAE Gain** |

---

## 3. Diagnostic Player Comparisons (V1 Baseline vs Candidate V2)

| Player | Prior Mins | V1 xMins | V2 xMins | V1 $P(\text{start})$ | V2 $P(\text{start})$ | V1 $xP$ | V2 $xP$ | Shrinkage Weight |
|---|---|---|---|---|---|---|---|---|
| **Taiwo Awoniyi** | 3,853m | 85.0m | **40.2m** | 90.0% | **51.8%** | 3.00 | **2.30** | $w=0.84$ |
| **William Osula** | 771m | 85.0m | **65.9m** | 90.0% | **77.5%** | 4.00 | **3.26** | $w=0.51$ |
| **Omar Marmoush** | 4,384m | 85.0m | **42.5m** | 90.0% | **54.0%** | 2.19 | **1.77** | $w=0.85$ |
| **Erling Haaland** | 8,004m | 85.0m | **59.2m** | 90.0% | **69.3%** | 3.36 | **3.57** | $w=0.91$ |
| **Dominic Calvert-Lewin** | 4,860m | 85.0m | **84.6m** | 90.0% | **94.0%** | 3.54 | **3.72** | $w=0.87$ |

---

## 4. Verification & Testing

- **Candidate Modules Created**:
  - `backend/ml/minutes_candidate_v2.py`
  - `backend/ml/xg_candidate_v2.py`
  - `backend/ml/xa_candidate_v2.py`
- **Frontend Panel**: Added `"MODEL v1 → CANDIDATE v2 COMPARISON"` card in [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html) labeled `CANDIDATE MODEL — NOT PRODUCTION`.
- **Unit Test Suite**: Created [`tests/test_phase3c8_low_sample_shrinkage.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3c8_low_sample_shrinkage.py) (**9/9 passed**).
- **Full Test Suite**: **86/86 automated tests passed cleanly**.
