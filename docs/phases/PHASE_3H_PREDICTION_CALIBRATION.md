# PHASE 3H — PREDICTION CALIBRATION LAYER REPORT

**Date**: 2026-08-21  
**Status**: `COMPLETED, DEPLOYED & EMPIRICALLY VERIFIED`  
**Dataset Evaluated**: `62,437 Historical Observations (Chronological Split: Train 2022-24, Val 2024-25, Test 2025-26)`  
**Deployed Model Version**: `expected_xp_calibrated_v1`  
**Pipeline Code Status**: `PROMOTED TO PRODUCTION (Engine updated with raw & calibrated xP)`  
**Test Suite Verification**: `102 / 102 tests passing`  

---

## 1. Executive Summary & Out-of-Sample Results

Phase 3H built, validated out-of-sample, and integrated a leak-free **Prediction Calibration Layer** (`expected_xp_calibrated_v1`) to solve the cross-position scale distortion established in Phase 3G.

### 🌟 Key Out-of-Sample Test Set Results (Untouched 2025/26 Season)

| Metric | RAW Production Model | CALIBRATED Model v1 | Absolute Improvement | Gate Status |
| :--- | :---: | :---: | :---: | :---: |
| **Mean Absolute Error (MAE)** | **1.8975 pts** | **1.8113 pts** | **-0.0862 pts/match** | **PASS** |
| **Root Mean Sq Error (RMSE)** | **2.7990 pts** | **2.7826 pts** | **-0.0164 pts/match** | **PASS** |
| **Spearman Rank Correlation ($\rho$)** | **0.3354** | **0.3561** | **+0.0207** | **PASS** |
| **Pearson Correlation ($r$)** | **0.2719** | **0.2850** | **+0.0131** | **PASS** |
| **Cross-Position Bias Gap** | **1.27 pts** | **0.84 pts** | **-0.43 pts gap reduction**| **PASS** |
| **Premium Attacker Underprediction**| **+1.03 pts** | **-0.48 pts** | **-0.55 pts bias reduction**| **PASS** |
| **Data Leakage** | Zero | Zero | Strictly Chronological | **PASS** |
| **Deployment Gate Decision** | N/A | N/A | N/A | **PROMOTED TO PRODUCTION (DEPLOY)** |

---

## 2. Component Calibration Multipliers Learned

The calibration layer was trained on pre-deadline data from 2022/23 to 2024/25:

1. **Clean Sheet Calibration (`cs_calibration_v1.pkl`)**: Isotonic regression mapping raw CS probabilities (34.5% mean) down to actual realized clean sheet rates (13.3% mean), eliminating the **-21.18% clean sheet overprediction bias**.
2. **Premium Attacker xG Calibration (`prem_xg_ratio`)**: **1.882x multiplier** applied to £10m+ premium attackers to correct LightGBM shrinkage on elite scorers. Standard attackers receive **0.984x**.
3. **Premium Attacker xA Calibration (`prem_xa_ratio`)**: **3.020x multiplier** applied to £10m+ premium playmakers to correct LightGBM shrinkage on elite creators. Standard playmakers receive **1.446x**.
4. **DEFCON Calibration**: Scaled static DEFCON probabilities by **0.65x** to match empirical defensive contribution rates.

---

## 3. Current 2026/27 GW1 Projections: RAW vs CALIBRATED Snapshot

Comparing raw vs calibrated projections for top players in GW1:

| Player Name | Pos | Price | Fixture | Raw xG | Cal xG | Raw CS | Cal CS | Raw xP | Calibrated xP | Calibration Adjustment | New GW1 Rank |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Erling Haaland** | FWD | £15.5m | BOU (H) | 0.388 | **0.730** | 42.0% | 14.2% | 4.22 | **6.53** | **+2.31 pts** | **#1** |
| **Bruno Fernandes**| MID | £12.0m | HUL (A) | 0.195 | **0.367** | 30.8% | 11.8% | 4.10 | **5.64** | **+1.54 pts** | **#2** |
| **Nico O'Reilly** | DEF | £6.5m | BOU (H) | 0.211 | 0.208 | 42.0% | 14.2% | 5.30 | **4.51** | **-0.79 pts** | **#3** |
| **Bukayo Saka** | MID | £9.5m | COV (H) | 0.243 | 0.239 | 68.8% | 14.2% | 4.51 | **4.31** | **-0.20 pts** | **#4** |
| **Joško Gvardiol** | DEF | £5.5m | BOU (H) | 0.158 | 0.155 | 42.0% | 14.2% | 5.02 | **4.02** | **-1.00 pts** | **#5** |
| **Riccardo Calafiori**| DEF | £5.5m | COV (H) | 0.160 | 0.157 | 68.8% | 14.2% | 5.88 | **3.89** | **-1.99 pts** | **#6** |
| **Cole Palmer** | MID | £9.5m | FUL (A) | 0.225 | 0.221 | 43.5% | 14.2% | 3.77 | **3.74** | **-0.03 pts** | **#7** |
| **Gabriel Magalhães**| DEF | £8.0m | COV (H) | 0.090 | 0.089 | 68.8% | 14.2% | 5.59 | **3.42** | **-2.17 pts** | **#8** |
| **João Pedro** | FWD | £7.5m | FUL (A) | 0.209 | 0.206 | 43.5% | 14.2% | 3.24 | **3.20** | **-0.04 pts** | **#9** |
| **David Raya** | GKP | £6.0m | COV (H) | 0.017 | 0.017 | 68.8% | 14.2% | 5.56 | **2.49** | **-3.07 pts** | **#10** |

---

## 4. Model Versioning & Production Integration

- **Artifacts Deployed**:
  - `backend/ml/models/cs_calibration_v1.pkl`
  - `backend/ml/models/expected_xp_calibrated_v1.json`
- **Projection Engine**:
  - Updated [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py) to compute both `raw_xp` and `calibrated_xp`.
  - Assigned production value `total_xp = calibrated_xp`.
- **Frontend UI**:
  - Updated [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html) health banner to display `Calibration Layer: expected_xp_calibrated_v1 (Active)`.

---

## 5. Stop Condition Confirmation

* **Phase 3H Prediction Calibration**: `COMPLETED & DEPLOYED`
* **All 7 Deployment Gate Criteria**: `PASSED`
* **Optimizer Executed**: `NO (Paused per instructions)`
* **GW1 Projections Verified**: `Erling Haaland #1 (6.53 xP), Bruno Fernandes #2 (5.64 xP)`
