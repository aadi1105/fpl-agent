# PHASE 3K — ATTACKING ROLE & PIECEWISE ROLE-AWARE CALIBRATION LAYER

OBJECTIVE:
Fix the mid-price (£6–8m) and sub-premium (£8–10m) attacker underprediction identified in Phase 3J, while preserving Phase 3H's successful premium (£10m+) calibration and low-sample safeguards.

Candidate Models Evaluated:
- MODEL A: Phase 3H calibration unchanged.
- MODEL B: Piecewise price-tier calibration only.
- MODEL C: Role-aware calibration only.
- MODEL D: Piecewise price-tier + Role-aware hierarchical calibration.

Key Requirements:
1. Leak-free chronological split (Train 2022-24, Val 2024-25, Untouched Test Set 2025-26).
2. Construct reproducible role proxies (Elite Striker, Standard Striker, Inside Forward, Creative Playmaker, Central Midfielder).
3. Evaluate out-of-sample RMSE, Spearman correlation, Pearson correlation, and price-tier biases (£6–8m, £8–10m, £10–12m, £12m+).
4. Specific player regressions (João Pedro, Calvert-Lewin, Marmoush, Osula, Awoniyi, Haaland, Bruno, Saka, Palmer).
5. 12-point Hard Deployment Gate.
6. DO NOT RUN OPTIMIZER. READ-ONLY CANDIDATE SELECTION & SNAPSHOT DIAGNOSTIC ONLY.
