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
- **`models/xa_v2.pkl`**: SHA256 `edde5f8dee0b01f0`

### 3. Bruno Fernandes Sanity Diagnostic
- **Stats**: £7.0m, 9.3% ownership (Consensus Rank #50).
- **v1 xP**: 4.43 | **v2 xP**: 2.22 (v2 Rank #262).
- **Classification**: **Category B (Missing feature / model structural limitation)**.
- **Root Cause**: Model lacks explicit set-piece/penalty ownership features and team-level offensive power weighting.

### 4. Optimizer Gate Results Across 4 Modes
- `CURRENT_GW_PLUS_3`: £100.0m spent | GW0 XI xP: 73.06 | 4-GW Weighted xP: 79.51 | Captain: Haaland
- `STRONG_XI_DUMP_BENCH`: £100.0m spent | GW0 XI xP: 73.06 | 4-GW Weighted xP: 80.65 | Captain: Haaland
- `BALANCED_BENCH`: £100.0m spent | GW0 XI xP: 71.91 | 4-GW Weighted xP: 78.81 | Captain: Haaland
- `MAXIMUM_SQUAD`: £100.0m spent | GW0 XI xP: 71.40 | 4-GW Weighted xP: 77.96 | Captain: Haaland
