# PHASE 3K — PIECEWISE PRICE-TIER & ROLE-AWARE CALIBRATION REPORT

**Date**: 2026-08-22  
**Status**: `COMPLETED, DEPLOYED & EMPIRICALLY VERIFIED`  
**Dataset Evaluated**: `62,437 Historical Observations Across 4 Seasons (2022/23 - 2025/26)`  
**Deployed Model Version**: `expected_xp_calibrated_v2`  
**Pipeline Code Status**: `PROMOTED TO PRODUCTION (Engine updated with v2 piecewise price-tier calibration)`  
**Test Suite Verification**: `102 / 102 tests passing`  

---

## 1. Executive Summary & Out-of-Sample Results

Phase 3K upgraded the prediction calibration layer from binary (£10m+ only) to **Piecewise Price-Tier and Role-Aware Calibration (`expected_xp_calibrated_v2`)** to resolve the mid-price attacker underprediction bias identified in Phase 3J.

### 🌟 Out-of-Sample Test Set Results (Untouched 2025/26 Season)

| Evaluation Metric | v1 Model (Binary £10m+) | v2 Model (Piecewise Price-Tier) | Calibration Improvement | Gate Status |
| :--- | :---: | :---: | :---: | :---: |
| **Root Mean Sq Error (RMSE)** | **2.7826 pts** | **2.7808 pts** | **-0.0018 pts/match** | **PASS** |
| **Spearman Rank Correlation ($\rho$)** | **0.3561** | **0.3622** | **+0.0061** | **PASS** |
| **Pearson Correlation ($r$)** | **0.2850** | **0.2891** | **+0.0041** | **PASS** |
| **£6.0–£8.0m Mid-Price Bias** | **+0.64 pts** | **+0.40 pts** | **-0.24 pts bias reduction** | **PASS** |
| **£8.0–£10.0m Sub-Premium Bias** | **+0.76 pts** | **+0.16 pts** | **-0.60 pts bias reduction** | **PASS** |
| **£10.0–£12.0m Premium Bias** | **-0.31 pts** | **+0.07 pts** | **Calibrated to +0.07 pts** | **PASS** |
| **£12.0m+ Super-Premium Bias** | **-0.70 pts** | **-0.48 pts** | **-0.22 pts bias reduction** | **PASS** |
| **Deployment Decision** | N/A | N/A | N/A | **PROMOTED TO PRODUCTION (DEPLOY)** |

---

## 2. GW1 Projections Comparison: Raw vs v1 Calibrated vs v2 Calibrated

| Rank | Player Name | Pos | Price | GW1 Fixture | Raw xG | Cal xG v2 | Raw xP | v1 Cal xP | v2 Cal xP | v2 Adjustment | Calibration Shift |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **#1** | **Erling Haaland** | FWD | £15.5m | BOU (H) | 0.388 | 0.678 | 4.22 | 6.52 | **6.26** | **+2.04 pts** | Super-Premium Calibrated |
| **#2** | **Bukayo Saka** | MID | £9.5m | COV (H) | 0.243 | 0.363 | 4.51 | 4.30 | **5.71** | **+1.20 pts** | **Sub-Premium Boost** |
| **#3** | **Bruno Fernandes**| MID | £12.0m | HUL (A) | 0.195 | 0.341 | 4.10 | 5.63 | **5.47** | **+1.37 pts** | Premium Calibrated |
| **#4** | **Rayan Cherki** | MID | £7.5m | BOU (H) | 0.220 | 0.284 | 4.64 | 4.46 | **5.38** | **+0.74 pts** | **Mid-Price Boost** |
| **#5** | **Phil Foden** | MID | £7.0m | BOU (H) | 0.232 | 0.287 | 4.34 | 4.27 | **4.96** | **+0.62 pts** | **Mid-Price Boost** |
| **#6** | **Ouattara Dango** | MID | £6.5m | TOT (H) | 0.250 | 0.297 | 4.15 | 4.23 | **4.78** | **+0.63 pts** | **Mid-Price Boost** |
| **#7** | **Cole Palmer** | MID | £9.5m | FUL (A) | 0.225 | 0.336 | 3.77 | 3.74 | **4.76** | **+0.99 pts** | **Sub-Premium Boost** |
| **#8** | **Nico O'Reilly** | DEF | £6.5m | BOU (H) | 0.211 | 0.208 | 5.30 | 4.50 | **4.51** | **-0.79 pts** | Defender CS Calibrated |
| **#9** | **Omar Marmoush** | FWD | £7.0m | BOU (H) | 0.262 | 0.325 | 3.46 | 3.52 | **4.03** | **+0.57 pts** | **Mid-Price Boost** |
| **#10**| **Joško Gvardiol** | DEF | £5.5m | BOU (H) | 0.158 | 0.155 | 5.02 | 4.01 | **4.02** | **-1.00 pts** | Defender CS Calibrated |
| **#11**| **Riccardo Calafiori**| DEF | £5.5m | COV (H) | 0.160 | 0.157 | 5.88 | 3.90 | **3.89** | **-1.99 pts** | Defender CS Calibrated |
| **#12**| **João Pedro** | FWD | £7.5m | FUL (A) | 0.209 | 0.270 | 3.24 | 3.19 | **3.67** | **+0.43 pts** | **Mid-Price Boost** |
| **#13**| **Dominic Calvert-Lewin**| FWD| £6.0m | NFO (A) | 0.223 | 0.254 | 2.87 | 3.17 | **3.40** | **+0.53 pts** | **Mid-Price Boost** |
| **#14**| **Gabriel Magalhães**| DEF | £8.0m | COV (H) | 0.090 | 0.089 | 5.59 | 3.42 | **3.42** | **-2.17 pts** | Defender CS Calibrated |

---

## 3. Documentation & Code Updates

1. [`backend/ml/models/expected_xp_calibrated_v2.json`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/models/expected_xp_calibrated_v2.json): Versioned model artifact.
2. [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py): Updated with v2 model loading and continuous price-tier scaling.
3. [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html): Health banner updated to display `Calibration Layer: expected_xp_calibrated_v2 (Piecewise Active)`.
4. [`docs/PROJECT_STATE.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/PROJECT_STATE.md), [`docs/ROADMAP.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/ROADMAP.md), [`docs/data/DATA_PIPELINE.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/data/DATA_PIPELINE.md): Single source of truth updated.
