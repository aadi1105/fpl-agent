# PHASE 3G — CROSS-POSITION xP CALIBRATION & VALUE AUDIT REPORT

**Date**: 2026-08-21  
**Status**: `COMPLETED & EMPIRICALLY VERIFIED`  
**Dataset Analyzed**: `62,437 Active Historical Evaluation Observations Across 4 Seasons (2022/23 - 2025/26)`  
**Pipeline Code Status**: `UNTOUCHED & READ-ONLY (Zero retrainings, zero optimizer calls, zero formula changes)`  
**Test Suite Verification**: `99 / 99 tests passing`  

---

## 1. Executive Summary & Fundamental Empirical Answers

Phase 3G evaluated the leak-free historical prediction framework across **62,437 active player-gameweek observations** to determine whether the absolute $xP$ scale is calibrated across positions and price tiers.

### 🌟 Fundamental Empirical Findings

1. **Question 1**: *"When the model predicts that a £5–7m defender should score 5–6 points and a £12–16m premium attacker should score 4–5 points, does historical reality support that difference?"*
   - **Answer**: **NO (EMPIRICALLY DISPROVED)**.
   - **Historical Cohort A (Defenders £4.5m–£7.0m projected at 4.5–6.0 xP)**: Mean predicted xP = **4.84 pts**, but actual realized mean FPL points = **2.74 pts** (Systematic Overprediction Bias: **-2.10 pts per match**!).
   - **Historical Cohort B (Premium Attackers £10.0m+ projected at 4.0–5.5 xP)**: Mean predicted xP = **4.66 pts**, but actual realized mean FPL points = **6.03 pts** (Systematic Underprediction Bias: **+1.37 pts per match**!).
   - **Conclusion**: In historical reality, the £10m+ attacker outscores the £5–7m defender by **+3.29 actual points per match**, even when the uncalibrated model ranks the defender higher!

2. **Position-Level Systematic Calibration Bias**:
   - **Defenders (DEF)**: Predicted mean = 2.27 xP, Actual mean = 1.72 pts $\implies$ **-0.54 pts Overpredicted**.
   - **Forwards (FWD)**: Predicted mean = 1.35 xP, Actual mean = 2.17 pts $\implies$ **+0.83 pts Underpredicted**.
   - **Premium Attackers (£10m+)**: Predicted mean = 2.98 xP, Actual mean = 5.05 pts $\implies$ **+2.07 pts Underpredicted**.

3. **Root Causes**:
   - **Clean Sheet Overprediction**: Mean predicted CS probability = **34.5%** vs actual realized CS rate = **13.3%** (**-21.18% CS bias**).
   - **Excessive ML xG/xA Shrinkage**: For £10m+ attackers, predicted xG = **0.253 xG** vs actual goals = **0.435** (+0.182 goals/match underpredicted) and predicted xA = **0.087 xA** vs actual assists = **0.253** (+0.166 assists/match underpredicted).

---

## 2. Section 3: Position-Level xP Calibration Table

Evaluation across 62,437 historical player-gameweek observations:

| Position | Observations | Predicted Mean xP | Actual Mean FPL Points | Calibration Bias (Actual - Pred) | MAE | RMSE | Median Error | Spearman Correlation ($\rho$) | Pearson Correlation ($r$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GKP** | 4,181 | 2.47 pts | 2.23 pts | **-0.24 pts** | 2.09 | 2.75 | -0.47 | 0.3136 | 0.3512 |
| **DEF** | 21,762 | 2.27 pts | 1.72 pts | **-0.54 pts** | 2.11 | 2.80 | -0.27 | 0.3039 | 0.3204 |
| **MID** | 29,046 | 1.54 pts | 1.96 pts | **+0.42 pts** | 1.67 | 2.71 | +0.46 | 0.3883 | 0.4410 |
| **FWD** | 7,448 | 1.35 pts | 2.17 pts | **+0.83 pts** | 1.89 | 3.13 | +0.65 | 0.3752 | 0.4150 |

---

## 3. Section 4: Predicted xP Bucket Calibration Table

| Predicted xP Bucket | Observations | Mean Predicted xP | Mean Actual FPL Points | Bucket Bias (Actual - Pred) | Bucket MAE | Calibration Diagnosis |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **0 – 2 xP** | 34,033 | 0.69 pts | 1.36 pts | **+0.68 pts** | 1.35 | Underpredicts bench/substitute appearances |
| **2 – 3 xP** | 10,814 | 2.56 pts | 2.31 pts | **-0.26 pts** | 2.02 | Well-calibrated mid-tier baseline |
| **3 – 4 xP** | 14,687 | 3.44 pts | 2.66 pts | **-0.77 pts** | 2.70 | Slight overprediction of mid-tier starters |
| **4 – 5 xP** | 2,537 | 4.31 pts | 3.28 pts | **-1.03 pts** | 3.25 | Overpredicts defenders with high CS prob |
| **5 – 6 xP** | 295 | 5.29 pts | 3.54 pts | **-1.76 pts** | 3.89 | Heavy defender CS overprediction |
| **6 – 7 xP** | 60 | 6.39 pts | 4.03 pts | **-2.36 pts** | 4.61 | Extreme defender CS overprediction |
| **7 – 8 xP** | 8 | 7.47 pts | 5.88 pts | **-1.59 pts** | 4.19 | Small sample high-return fixtures |
| **8+ xP** | 3 | 8.08 pts | 2.67 pts | **-5.42 pts** | 5.42 | Extreme outlier overprediction |

---

## 4. Section 5: Matched Historical Cohort Comparison

Comparing matched historical cohorts to test cross-position balance:

| Evaluation Metric | Cohort A: Defenders (£4.5–£7.0m, xP 4.5–6.0) | Cohort B: Premium Attackers (£10.0m+, xP 4.0–5.5) | Cross-Cohort Delta |
| :--- | :---: | :---: | :---: |
| **Observation Count** | 383 observations | 173 observations | N/A |
| **Mean Predicted xP** | **4.84 pts** | **4.66 pts** | Defender +0.18 xP |
| **Mean Actual FPL Points** | **2.74 pts** | **6.03 pts** | **Attacker +3.29 Actual Pts** |
| **Calibration Bias** | **-2.10 pts (Overpredicted)** | **+1.37 pts (Underpredicted)** | **3.47 Pts Bias Gap** |

---

## 5. Section 6: Premium Attacker Audit (£10m+)

Evaluating 612 historical observations of £10m+ premium attackers (Salah, Haaland, Saka, Son, Bruno, Palmer, Kane, De Bruyne):

| Metric | Mean Predicted Model Value | Mean Actual Realized Outcome | Model Calibration Bias | Calibration Diagnosis |
| :--- | :---: | :---: | :---: | :--- |
| **Match xG** | **0.253 xG** | **0.435 goals** | **+0.182 goals/match** | Severe ML xG shrinkage on elite scorers |
| **Match xA** | **0.087 xA** | **0.253 assists** | **+0.166 assists/match** | Severe ML xA shrinkage on elite playmakers |
| **Total xP** | **2.98 pts** | **5.05 pts** | **+2.07 pts/match** | Premium attackers systematically underpredicted |

---

## 6. Section 11: Price Tier Value Analysis (xP / £m vs Actual / £m)

| Price Tier | Observations | Mean Predicted xP / £m | Mean Actual Points / £m | Value Bias | Key Insight |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **£4.0 – £5.0m** | 32,344 | 0.39 xP/£m | 0.32 pts/£m | **-0.06** | Budget players slightly overvalued |
| **£5.0 – £6.0m** | 18,809 | 0.35 xP/£m | 0.41 pts/£m | **+0.06** | Mid-price starters well-calibrated |
| **£6.0 – £8.0m** | 7,764 | 0.31 xP/£m | 0.43 pts/£m | **+0.12** | High mid-price players undervalued |
| **£8.0 – £10.0m** | 1,396 | 0.28 xP/£m | 0.42 pts/£m | **+0.14** | Sub-premiums undervalued |
| **£10.0 – £12.0m**| 290 | 0.23 xP/£m | 0.40 pts/£m | **+0.17** | Premiums undervalued per £m |
| **£12.0m+** | 322 | 0.25 xP/£m | 0.43 pts/£m | **+0.17** | Super-premiums (Haaland/Salah) severely undervalued per £m |

---

## 7. Section 13: Current 2026/27 Snapshot Diagnostic Table

| Player Name | Pos | Price | Fixture | xMins | Match xG | Match xA | CS Prob | DEFCON Prob | Predicted xP | xP / £m | Diagnostic Value |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Riccardo Calafiori**| DEF | £5.5m | COV (H) | 83.4m | 0.160 | 0.051 | 68.8% | 9.6% | **5.88** | **1.07** | Inflated by 68.8% CS (+2.55 pts) |
| **Gabriel Magalhães**| DEF | £8.0m | COV (H) | 83.4m | 0.090 | 0.070 | 68.8% | 6.6% | **5.59** | **0.70** | Inflated by 68.8% CS (+2.55 pts) |
| **David Raya** | GKP | £6.0m | COV (H) | 84.3m | 0.017 | 0.009 | 68.8% | 0.0% | **5.56** | **0.93** | Inflated by 68.8% CS (+2.55 pts) |
| **Nico O'Reilly** | DEF | £6.5m | BOU (H) | 82.7m | 0.211 | 0.090 | 42.0% | 13.9% | **5.30** | **0.82** | Inflated by 42.0% CS (+1.54 pts) & DEF rules |
| **Joško Gvardiol** | DEF | £5.5m | BOU (H) | 82.7m | 0.158 | 0.061 | 42.0% | 19.1% | **5.02** | **0.91** | Inflated by 42.0% CS (+1.54 pts) & DEFCON |
| **Bukayo Saka** | MID | £9.5m | COV (H) | 83.7m | 0.243 | 0.158 | 68.8% | 1.5% | **4.51** | **0.47** | Underpredicted xG/xA vs actual returns |
| **Erling Haaland** | FWD | £15.5m | BOU (H) | 84.0m | 0.388 | 0.085 | 42.0% | 0.0% | **4.22** | **0.27** | Severe xG shrinkage (0.388 vs ~0.70 actual) |
| **Bruno Fernandes** | MID | £12.0m | HUL (A) | 83.6m | 0.195 | 0.122 | 30.8% | 2.9% | **4.10** | **0.34** | Underpredicted xG/xA & away CS |
| **Cole Palmer** | MID | £9.5m | FUL (A) | 83.8m | 0.225 | 0.074 | 43.5% | 0.2% | **3.77** | **0.40** | Underpredicted xG/xA & away CS |
| **João Pedro** | FWD | £7.5m | FUL (A) | 84.9m | 0.209 | 0.059 | 43.5% | 0.0% | **3.24** | **0.43** | Moderate xG & 0 defensive pts |

---

## 8. Answers to the 10 Critical Decision Questions

1. **Is a 5.5 xP defender historically worth approximately 5.5 actual FPL points?**
   * **Answer**: **NO (MASSIVE OVERESTIMATION)**. Empirically, £4.5m–£7.0m defenders with predicted xP between 4.5 and 6.0 (mean predicted: 4.84 xP) **ACTUALLY SCORE ONLY 2.74 FPL POINTS** (a systematic overprediction bias of **-2.10 points per match**!).
2. **Is a 4.2 xP premium attacker historically worth approximately 4.2 actual FPL points?**
   * **Answer**: **NO (MASSIVE UNDERESTIMATION)**. Empirically, £10.0m+ premium attackers with predicted xP between 4.0 and 5.5 (mean predicted: 4.66 xP) **ACTUALLY SCORE 6.03 FPL POINTS** (a systematic underprediction bias of **+1.37 points per match**!).
3. **Does the current system systematically undervalue premium attackers?**
   * **Answer**: **YES**. Across 612 historical observations of £10m+ premium attackers, predicted mean xP is **2.98 xP**, while actual realized mean FPL points is **5.05 points** (underpredicted by **+2.07 points per match**!). Both xG (0.253 pred vs 0.435 actual) and xA (0.087 pred vs 0.253 actual) are severely compressed by ML model shrinkage.
4. **Does the current system systematically overvalue defenders?**
   * **Answer**: **YES**. Across 21,762 defender observations, predicted mean xP is **2.27 xP** while actual mean FPL points is **1.72 points** (overpredicted by **-0.54 points per match** across all defenders, and up to **-2.10 points per match** for top-tier defenders projected at 4.5+ xP!).
5. **Is the CS model calibrated?**
   * **Answer**: **NO**. Across 25,943 defender and goalkeeper observations, the mean predicted clean sheet probability is **34.5%**, while the actual realized clean sheet rate is **13.3%** (a clean sheet overprediction bias of **-21.18 percentage points**!).
6. **Is the DEFCON model calibrated?**
   * **Answer**: **PARTIALLY (OVERVALUED IN COMBINATION WITH CS)**. Adding static DEFCON probabilities (~0.14 $\implies$ +0.26 pts) on top of overpredicted CS probabilities further inflates defender point baselines.
7. **Is the xG model calibrated for elite attackers?**
   * **Answer**: **NO (EXCESSIVE ML SHRINKAGE FOR ELITE PLAYERS)**. For £10m+ attackers, predicted xG is **0.253 xG** vs actual **0.435 goals** (+0.182 goals/match underpredicted). Global LightGBM shrinkage pulls elite goalscorers down toward the league average.
8. **Is the xA model calibrated for elite attackers?**
   * **Answer**: **NO (EXCESSIVE ML SHRINKAGE FOR ELITE PLAYERS)**. For £10m+ attackers, predicted xA is **0.087 xA** vs actual **0.253 assists** (+0.166 assists/match underpredicted).
9. **Is the absolute xP scale comparable across positions?**
   * **Answer**: **NO (STRUCTURALLY BIASED CROSS-POSITION SCALE)**. A 5.0 xP defender delivers **~2.74 actual points**, whereas a 5.0 xP attacker delivers **~6.03 actual points**. The absolute point scale across positions is NOT on a 1-to-1 comparable footing.
10. **Is the current xP safe to feed directly into the optimizer?**
    * **Answer**: **NO (UNSAFE IN CURRENT UNCALIBRATED STATE)**. Feeding these uncalibrated xP values directly into a MILP solver will cause the optimizer to select 5 budget/mid-price defenders (projected at 5.0–5.8 xP) and zero premium attackers (projected at 4.1–4.2 xP), which is an empirically sub-optimal FPL squad selection.

---

## 9. Stop Condition Confirmation

* **Phase 3G Calibration Audit**: `COMPLETED`
* **Historical Evaluation Dataset**: `62,437 Observations Evaluated`
* **Optimizer Executed**: `NO (Paused per instructions)`
* **ML Models Retrained**: `NO (Paused per instructions)`
* **Projections Modified**: `NO (Read-only evaluation)`
