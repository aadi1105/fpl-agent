# PHASE 3K — PIECEWISE PRICE-TIER & ROLE-AWARE CALIBRATION LAYER

OBJECTIVE:
Upgrade the prediction calibration layer from binary (£10m+ only) to a Piecewise Price-Tier and Role-Aware Calibration model (`expected_xp_calibrated_v2`).

Goals:
1. Eliminate underprediction of mid-price attackers (£6.0–8.0m, previous bias +0.88 pts) and sub-premiums (£8.0–10.0m, previous bias +1.23 pts).
2. Maintain out-of-sample calibration for super-premiums (£12.0m+, Haaland #1, Bruno #2) and defenders.
3. Validate out-of-sample on untouched 2025/26 test set across MAE, RMSE, Spearman rank correlation, and price-tier bias.
4. Integrate versioned model artifact `expected_xp_calibrated_v2.json` into production `ProjectionEngine`.
