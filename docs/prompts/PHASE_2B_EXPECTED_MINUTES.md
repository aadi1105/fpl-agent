# Phase 2B Prompt: Expected Minutes ML Model

```text
FPL AI — PHASE 2B: EXPECTED MINUTES ML MODEL

OBJECTIVE:
Train, evaluate, backtest, and compare Expected Minutes / Availability ML models against baseline heuristics on historical_minutes_dataset.csv.

PREDICTION TASKS:
MODEL A: P(start) — target_started (Binary Classifier)
MODEL B: Expected minutes — target_minutes (Regressor)
MODEL C: P(60+ minutes) — target_60_plus (Binary Classifier)
MODEL D: P(0 minutes) — target_zero_minutes (Binary Classifier)

CHRONOLOGICAL SPLIT:
TRAIN: 2022/23 + 2023/24
VALIDATION: 2024/25 (Used for model selection & tuning)
TEST: 2025/26 (Evaluated ONCE after model selection — untouched during tuning)

EVALUATION:
- Classifiers: Log Loss, Brier Score, ROC-AUC, PR-AUC, Probability Calibration.
- Regressor: MAE, RMSE, Median Absolute Error.
- Small-sample behavior (<300, 300-600, 600-1000, >1000 mins).
- Out-of-sample comparison vs Deterministic Baseline heuristics.

RULES:
- DO NOT train xG/xA/Clean Sheet/DEFCON yet.
- DO NOT replace current production projection engine until explicitly approved.
- DO NOT modify optimizer.
```
