# PHASE 3K — ATTACKING ROLE & PIECEWISE CALIBRATION LAYER

OBJECTIVE:
Build, evaluate out-of-sample on an untouched 2025/26 test set, and deploy the Piecewise Price-Tier and Role-Aware Calibration Layer (`expected_xp_calibrated_v2`).

Candidate Models Evaluated:
- MODEL A: Phase 3H calibration unchanged.
- MODEL B: Piecewise price-tier calibration only.
- MODEL C: Role-aware calibration only.
- MODEL D: Piecewise price-tier + Role-aware hierarchical calibration.

Evaluation Metrics:
- Out-of-sample xP MAE, RMSE, Spearman rank correlation, Pearson correlation.
- Price-tier bias (£6–8m, £8–10m, £10–12m, £12m+).
- Specific player regression tests (João Pedro, Calvert-Lewin, Marmoush, Osula, Awoniyi, Haaland, Bruno, Saka, Palmer).
- 12-point Hard Deployment Gate.
