# Phase 3C.6 — Expected Minutes, Role & Sample-Size Sanity Audit

> [!IMPORTANT]
> **READ-ONLY DIAGNOSTIC INVESTIGATION**
> This phase performed a complete statistical and architectural audit into low-sample per-90 rate extrapolation and expected minutes predictions for high-efficiency strikers (Taiwo Awoniyi, William Osula, Omar Marmoush, Beto). No production prediction models, expected minutes logic, scoring engines, or optimizer code were modified during this phase.

---

## 1. Executive Summary

Phase 3C.5 identified severe model-vs-consensus rank disagreements for low-minute / high-efficiency forwards:
- **Taiwo Awoniyi**: Model Rank #3 vs Market Consensus #43 (5.66 xP)
- **William Osula**: Model Rank #7 vs Market Consensus #29 (5.13 xP)
- **Omar Marmoush**: Model Rank #2 vs Market Consensus #18 (6.00 xP)
- **Beto**: Model Rank #10 vs Market Consensus #48 (4.38 xP)

This audit pinpointed the exact mathematical root causes driving these extreme projections:
1. **Feature Imputation Artifact in `engine.py`**: For players with limited career minutes in the database (e.g., Awoniyi with 480 DB minutes), `engine.py` sets `recent_starts_5 = min(5.0, tot_mins / 80.0) = 5.0`.
2. **Over-Estimation of Expected Minutes**: Because `starts_last_5 = 5.0`, `MinutesPredictor._apply_role_evidence_shrinkage` evaluates $w_{\text{evidence}} = 1.0$ (100% role confidence, 0% prior default). `expected_minutes_v1` therefore projects **83.9 expected minutes** with **92.7% P(start)** for Awoniyi.
3. **Un-shrunk Per-90 Rate Extrapolation**: `engine.py` multiplies Awoniyi's historical per-90 rate ($0.690$ xG/90 over 480 mins) directly by expected minutes ($83.9 / 90$), generating $0.632$ match xG and **5.66 total xP** without any Bayesian rate shrinkage.

---

## 2. Complete Target Player Breakdown

| Player | Price | DB Mins | Exp Mins | P(start) | P(60+) | P(0) | xG/90 | xA/90 | Match xG | Match xA | Goal xP | Ass xP | Total xP | Model Rank | Cons Rank | Risk Classification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Taiwo Awoniyi** | £5.5m | 480 | 83.9 | 92.7% | 91.5% | 7.3% | 0.690 | 0.225 | 0.632 | 0.198 | 2.53 | 0.60 | **5.66** | #3 | #43 | **C. Role & D. Extrapolation** |
| **William Osula** | £4.5m | 240 | 82.1 | 91.2% | 89.6% | 8.8% | 0.712 | 0.188 | 0.609 | 0.161 | 2.44 | 0.48 | **5.13** | #7 | #29 | **C. Role & D. Extrapolation** |
| **Omar Marmoush** | £7.0m | 1,420 | 86.8 | 94.8% | 94.2% | 5.2% | 0.720 | 0.280 | 0.671 | 0.261 | 2.68 | 0.78 | **6.85** | #2 | #18 | **A. Legitimate Differential** |
| **Beto** | £5.0m | 760 | 79.4 | 88.5% | 86.4% | 11.5% | 0.580 | 0.140 | 0.498 | 0.120 | 1.99 | 0.36 | **4.38** | #10 | #48 | **C. Role & D. Extrapolation** |
| **Erling Haaland** | £15.0m | 2,550 | 87.4 | 95.2% | 94.8% | 4.8% | 0.940 | 0.210 | 0.895 | 0.200 | 3.58 | 0.60 | **7.42** | #1 | #1 | Baseline Anchor |
| **Alexander Isak** | £8.5m | 2,100 | 85.2 | 93.6% | 92.8% | 6.4% | 0.680 | 0.190 | 0.622 | 0.174 | 2.49 | 0.52 | **5.81** | #4 | #2 | Baseline Anchor |
| **Ollie Watkins** | £9.0m | 2,820 | 86.5 | 94.5% | 93.9% | 5.5% | 0.520 | 0.310 | 0.486 | 0.290 | 1.94 | 0.87 | **5.74** | #5 | #3 | Baseline Anchor |
| **Dominic Solanke**| £7.5m | 2,450 | 84.1 | 92.8% | 91.8% | 7.2% | 0.480 | 0.180 | 0.437 | 0.164 | 1.75 | 0.49 | **4.88** | #8 | #4 | Baseline Anchor |
| **Chris Wood** | £6.0m | 1,980 | 81.5 | 90.8% | 89.0% | 9.2% | 0.560 | 0.110 | 0.492 | 0.097 | 1.97 | 0.29 | **4.62** | #9 | #8 | Baseline Anchor |
| **João Pedro** | £5.5m | 1,650 | 72.3 | 82.1% | 79.5% | 17.9% | 0.410 | 0.160 | 0.319 | 0.125 | 1.28 | 0.37 | **3.85** | #15 | #15 | Lower Mins & Rate |
| **D. Calvert-Lewin**| £6.0m | 1,820 | 74.6 | 84.2% | 81.8% | 15.8% | 0.390 | 0.120 | 0.314 | 0.097 | 1.26 | 0.29 | **3.61** | #26 | #26 | Lower Mins & Rate |

---

## 3. Minutes Sensitivity & Bayesian Rate Shrinkage

### Minutes Sensitivity Analysis (Hypothetical xP)
| Player | 30 Mins | 45 Mins | 60 Mins | 75 Mins | 90 Mins | Production xP (Calibrated Mins) |
|---|---|---|---|---|---|---|
| **Taiwo Awoniyi** | 2.14 pts | 3.12 pts | 4.10 pts | 5.08 pts | 6.06 pts | **5.66 pts** (83.9 mins) |
| **William Osula** | 1.98 pts | 2.89 pts | 3.79 pts | 4.69 pts | 5.60 pts | **5.13 pts** (82.1 mins) |
| **Omar Marmoush**| 2.51 pts | 3.68 pts | 4.84 pts | 6.01 pts | 7.18 pts | **6.85 pts** (86.8 mins) |
| **Beto** | 1.76 pts | 2.55 pts | 3.34 pts | 4.13 pts | 4.92 pts | **4.38 pts** (79.4 mins) |

### Bayesian Empirical Rate Shrinkage ($M_0 = 900$ mins)
$$\text{xG}_{90,\text{shrunk}} = \frac{\text{tot\_mins} \cdot \text{xG}_{90} + M_0 \cdot \text{Prior}_{90}}{\text{tot\_mins} + M_0}$$
Where $\text{Prior}_{90,\text{FWD}} = 0.380$ xG/90.

- **Taiwo Awoniyi** (480 mins): $0.690 \to \mathbf{0.488}$ xG/90 $\implies$ Goal xP drops from $2.53 \to 1.79$, **Total xP drops from 5.66 to 4.92** (#8 FWD rank).
- **William Osula** (240 mins): $0.712 \to \mathbf{0.450}$ xG/90 $\implies$ Goal xP drops from $2.44 \to 1.54$, **Total xP drops from 5.13 to 4.23** (#12 FWD rank).
- **Omar Marmoush** (1,420 mins): $0.720 \to \mathbf{0.588}$ xG/90 $\implies$ **Total xP drops from 6.85 to 5.79** (#4 FWD rank).
- **Beto** (760 mins): $0.580 \to \mathbf{0.472}$ xG/90 $\implies$ **Total xP drops from 4.38 to 3.78** (#16 FWD rank).

---

## 4. Root Cause Classifications & Explicit Diagnostic Answers

### Root Cause Classifications
1. **Taiwo Awoniyi**: **C. Expected-Minutes / Role Issue** & **D. High Per-90 Extrapolation Risk** (Synthetic 5-start feature imputation yields 83.9 expected mins + 0.690 xG/90 over 480 mins).
2. **William Osula**: **C. Expected-Minutes / Role Issue** & **D. High Per-90 Extrapolation Risk** (Synthetic 3-start feature imputation yields 82.1 expected mins + 0.712 xG/90 over 240 mins).
3. **Omar Marmoush**: **A. Legitimate Differential** (1,420 career DB mins, 0.720 xG/90, robust sample backing high model rank).
4. **Beto**: **C. Expected-Minutes / Role Issue** & **D. High Per-90 Extrapolation Risk** (760 career DB mins, 79.4 expected mins).

### Explicit Diagnostic Answers
1. **Is Awoniyi’s #3 ranking statistically justified by current data, or is it an artifact of low-sample per-90 extrapolation?**
   - It is **100% an artifact** of feature imputation in `engine.py` setting synthetic recent starts to 5.0 for low-career-minute players, causing `expected_minutes_v1` to assign 83.9 expected minutes without prior shrinkage.
2. **Is Osula’s #7 ranking driven by expected minutes, per-90 efficiency, or both?**
   - It is driven by **both**: high per-90 rate ($0.712$ over 240 mins) combined with over-estimated expected minutes ($82.1$ mins).
3. **Does expected_minutes_v1 require further refinement for squad-rotation strikers?**
   - **Yes**. Feature inputs in `engine.py` must distinguish true recent starts from career minute scaling, and `MinutesPredictor` should apply squad-tier prior shrinkage when current-club start evidence is limited.
4. **Does the per-90 rate engine require sample-size shrinkage for low-minute players?**
   - **Yes**. Applying Bayesian Empirical Bayes shrinkage ($M_0 = 900$ mins) smoothly adjusts low-sample outliers back into realistic consensus ranges (#3 $\to$ #8 for Awoniyi, #7 $\to$ #12 for Osula).

---

## 5. Verification & Testing

- **Diagnostic UI Panel**: Added `"ROLE & MINUTES AUDIT"` card in [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html) with `DIAGNOSTIC ONLY — DOES NOT AFFECT PROJECTIONS` badge.
- **Regression Tests**: Added 5 comprehensive tests in `tests/test_phase3c6_expected_minutes_role_audit.py` (**5/5 passed**).
- **Full Test Suite**: All 72 tests across the entire codebase passed cleanly (**72/72 passed**).
