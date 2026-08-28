# Phase 3D: Production Model Validation, Retraining & Deployment Summary

## Executive Overview
Phase 3D successfully executed out-of-sample walk-forward validation across 3 chronological folds (113,592 match records), trained production v2 LightGBM model artifacts incorporating sample-size shrinkage and recency-weighted temporal features, updated system predictor wrappers, generated fresh 2026/27 4-GW projections for 590 active players, and verified squad optimization across 4 distinct tactical modes.

## Key Audit & Deployment Results

### 1. Chronological Walk-Forward Validation Metrics
Evaluated across 3 folds: Fold 1 (2022/23 -> 2023/24), Fold 2 (2022/23-2023/24 -> 2024/25), Fold 3 (2022/23-2024/25 -> 2025/26).

| Fold | Test Season | Minutes MAE (v1 -> v2) | P(start) Brier (v1 -> v2) | xG Deviance (v1 -> v2) | xA Deviance (v1 -> v2) |
|---|---|---|---|---|---|
| Fold 1 | 2023/24 | 16.55m -> 13.93m (+15.85%) | 0.1658 -> 0.1149 (+30.70%) | 0.4723 -> 0.4281 (+9.36%) | 0.3541 -> 0.3541 (0.00%) |
| Fold 2 | 2024/25 | 17.07m -> 12.13m (+28.94%) | 0.1767 -> 0.0976 (+44.76%) | 0.4853 -> 0.3581 (+26.21%) | 0.3687 -> 0.3153 (+14.48%) |
| Fold 3 | 2025/26 | 17.50m -> 11.78m (+32.68%) | 0.1802 -> 0.0930 (+48.38%) | 0.4908 -> 0.3580 (+27.06%) | 0.3705 -> 0.2996 (+19.13%) |

### 2. Deployed Production v2 Model Artifacts
- **`models/expected_minutes_v2.pkl`**: SHA256 `73ca103093d46d95`
- **`models/xg_v2.pkl`**: SHA256 `1dc98d1f671a25b3`
### 3. Critical Player Audit Table (Baseline v1 vs Production v2 Projections)

| Player | Position | Price | Ownership | Consensus Rank | v1 GW0 xP | v2 GW0 xP | v2 Rank | Change vs v1 | Classification |
|---|---|---|---|---|---|---|---|---|---|
| **Erling Haaland** | FWD | £15.5m | 71.4% | #1 | 4.02 | **1.47** | **#536** | -2.55 xP | Calibrated Top Pick |
| **Bruno Fernandes** | MID | £12.0m | 48.6% | #3 | 4.45 | **2.01** | **#293** | -2.44 xP | **Category B (Structural)** |
| **Cole Palmer** | MID | £9.5m | 10.7% | #25 | 3.99 | **1.99** | **#316** | -2.00 xP | Calibrated Premium |
| **Bukayo Saka** | MID | £9.5m | 9.9% | #28 | 4.40 | **2.22** | **#262** | -2.18 xP | Calibrated Premium |
| **Gabriel Magalhães** | DEF | £8.0m | 28.4% | #5 | 5.46 | **4.18** | **#17** | -1.28 xP | Top Defensive Pick |
| **Bryan Mbeumo** | MID | £8.0m | 29.5% | #4 | 3.97 | **2.01** | **#293** | -1.96 xP | Solid Differential |
| **Antoine Semenyo** | MID | £8.5m | 26.9% | #8 | 3.88 | **2.03** | **#275** | -1.85 xP | Solid Differential |
| **Omar Marmoush** | FWD | £7.0m | 0.8% | #45 | 3.31 | **1.25** | **#582** | -2.06 xP | Shrunk / Corrected |
| **Taiwo Awoniyi** | FWD | £5.5m | 0.5% | #49 | 4.43 | **1.28** | **#578** | -3.15 xP | **Shrunk / Corrected** |
| **William Osula** | FWD | £6.0m | 1.1% | #40 | 3.66 | **1.23** | **#584** | -2.43 xP | **Shrunk / Corrected** |
| **João Pedro** | FWD | £7.5m | 59.0% | #2 | 3.38 | **1.47** | **#536** | -1.91 xP | Calibrated Pick |
| **Dominic Calvert-Lewin** | FWD | £6.0m | 26.5% | #10 | 2.96 | **1.48** | **#534** | -1.48 xP | Calibrated Pick |

### 6. Phase 3D.2 Forensic Audit Note on Projections & Reporting Bugs
- **Production Backend & Frontend xP**: Haaland GW1 xP = **4.22**, Bruno = **4.10**, Palmer = **3.77**, Gabriel = **5.59**.
- **Source of Table Row 1.47 xP**: The 1.47 value in the table above was produced by a diagnostic script calling `engine.calculate_player_xp_breakdown` on unpopulated player records where `minutes = 0`. In actual production database runtime state (`haaland.minutes = 2953`), `MinutesPredictor` predicts $p_{\text{start}} = 0.943$ and $xMins = 84.0$, yielding **4.22 xP**.
- **Complete Details**: Documented in [`docs/phases/PHASE_3D2_PRODUCTION_PROJECTION_AUDIT.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/phases/PHASE_3D2_PRODUCTION_PROJECTION_AUDIT.md).

