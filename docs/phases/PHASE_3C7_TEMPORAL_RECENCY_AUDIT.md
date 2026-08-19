# Phase 3C.7 — Temporal / Recency & Current-Form Audit

> [!IMPORTANT]
> **STRICT READ-ONLY RESEARCH & BACKTESTING PHASE**
> This phase empirically audited whether temporal / recent-form features improve out-of-sample prediction of future player performance across Expected Minutes, Expected Goals ($xG$), and Expected Assists ($xA$). No production prediction models, expected minutes algorithms, scoring engines, or optimizer code were modified during this phase.

---

## 1. Core Research Question & Empirical Findings

**Research Question**: *"Does recent information improve out-of-sample prediction of future player performance compared with our current historical baseline?"*

### Empirical Results Summary (Evaluated on Untouched 2025/26 Test Set)

| Target Component | Baseline Metric | Recency Model Metric | Out-of-Sample Improvement | Optimal Window | Recommended Strategy |
|---|---|---|---|---|---|
| **Expected Minutes** | MAE: 24.47m (Brier: 0.1587) | MAE: 14.38m (Brier: 0.0895) | **+41.24% MAE (+43.65% Brier)** | Last 3 / 5 Starts & Apps | **DEPLOY STRONG RECENCY** |
| **Expected Goals ($xG$)** | Deviance: 0.1681 (MAE: 0.0775) | Deviance: 0.1036 (MAE: 0.0477) | **+38.39% Deviance (+38.45% MAE)** | Multi-Window ($xG/90$ + Threat/5) | **DEPLOY HYBRID / SHRINKAGE** |
| **Expected Assists ($xA$)** | Deviance: 0.0954 (MAE: 0.0460) | Deviance: 0.0729 (MAE: 0.0355) | **+23.56% Deviance (+22.83% MAE)** | Last 5 / 10 $xA/90$ | **DEPLOY HYBRID / SHRINKAGE** |

---

## 2. Component-by-Component Recency Breakdown

### A. Expected Minutes
- **Baseline**: Static career prior + total minutes (`tot_mins_prior`) $\implies$ MAE **24.47 mins**, $P(\text{start})$ Brier Score **0.1587**.
- **Recency Model**: Baseline + `mins_last_3`, `mins_last_5`, `starts_last_5` $\implies$ MAE **14.38 mins**, $P(\text{start})$ Brier Score **0.0895**.
- **Key Insight**: Recent starting role evidence (starts in last 3-5 matches) is the single most predictive feature for future expected minutes.

### B. Expected Goals ($xG$)
- **Model A (Career Baseline)**: Deviance `0.1681` (MAE `0.0775`).
- **Model B (+ Last 10)**: Deviance `0.1377` (**+18.08% improvement**).
- **Model C (+ Last 5)**: Deviance `0.1345` (**+20.00% improvement**).
- **Model D (+ Last 3)**: Deviance `0.1327` (**+21.07% improvement**).
- **Model E (Multi-Window Ensemble)**: Deviance `0.1036` (**+38.39% improvement**).
- **Key Insight**: Combining multi-window underlying process features ($xG/90$ last 3, 5, 10 + threat/90 last 5) dramatically improves future $xG$ prediction.

### C. Expected Assists ($xA$)
- **Model A (Career Baseline)**: Deviance `0.0954` (MAE `0.0460`).
- **Model B (+ Last 10)**: Deviance `0.0824` (**+13.66% improvement**).
- **Model C (+ Last 5)**: Deviance `0.0768` (**+19.45% improvement**).
- **Model D (+ Last 3)**: Deviance `0.0759` (**+20.44% improvement**).
- **Model E (Multi-Window Ensemble)**: Deviance `0.0729` (**+23.56% improvement**).
- **Key Insight**: $xA$ demonstrates higher historical persistence than $xG$; longer recency windows (last 5 to 10 matches) produce smoother predictions.

---

## 3. Sample-Size Interaction & Regression to the Mean

### Sample-Size Interaction Table
| Historical Career Mins | Sample Count (N) | Baseline Deviance | Recency Deviance | Recency Out-of-Sample Gain |
|---|---|---|---|---|
| **<300 mins** | 2,663 | 0.0546 | 0.0520 | **+4.73%** (Low sample, high noise) |
| **300–600 mins** | 672 | 0.1529 | 0.1495 | **+2.22%** (Low sample, high noise) |
| **600–1,000 mins** | 1,710 | 0.1379 | 0.1156 | **+16.14%** (Moderate gain) |
| **1,000–2,000 mins** | 4,172 | 0.1521 | 0.1253 | **+17.62%** (High gain) |
| **2,000+ mins** | 20,540 | 0.1891 | 0.1481 | **+21.66%** (Maximum gain) |

> [!TIP]
> **Bayesian Recency Rule**: For low-sample players (<600 minutes), raw short-window recency introduces noise. Heavy Bayesian shrinkage towards squad/position priors is necessary. For established players (>1,000 minutes), recency provides massive predictive gains.

### Goals vs. Process Stats (xG/90 vs Goals/90)
- Correlation of `xg_90_last_5` with Future $xG$: **0.2284**
- Correlation of `goals_90_last_5` with Future $xG$: **0.1712**
- **Finding**: Underlying process statistics ($xG/90$) predict future attacking returns **33.4% better** than actual goals scored ($Goals/90$).

### Form Stability & Regression to the Mean
- Evaluated 366 match instances where players experienced an extreme 3-match form spike ($\text{xG/90}_{\text{last\_3}} \ge 0.70$, avg $0.984$ xG/90).
- In the subsequent match, their actual performance regressed to **0.220 xG** (very close to their career average of **0.250 xG/90**).
- **Regressed Rate**: Only **25.20%** of short-term form spikes persist; ~75% regresses to long-term priors.

---

## 4. Case Studies & Target Player Analysis

1. **Omar Marmoush (Man City, 1,093 DB mins)**:
   - Career $xG/90 = 0.417$, Last 10 $xG/90 = 0.497$, Last 5 $xG/90 = 0.319$.
   - *Finding*: Multi-window recency smoothly captures his role transition without overreacting to individual match spikes.
2. **Dominic Calvert-Lewin (Leeds, 4,860 DB mins)**:
   - Career $xG/90 = 0.413$, Last 10 $xG/90 = 0.568$, Last 5 $xG/90 = 0.486$.
   - *Finding*: Recent Leeds performance (900 mins in last 10) provides higher predictive accuracy for current output than older Everton historical baseline.
3. **Taiwo Awoniyi (Nott'm Forest, 3,853 DB mins)**:
   - Career $xG/90 = 0.220$, Last 5 $xG/90 = 0.704$, Last 5 Mins = 184 mins (2 starts).
   - *Finding*: Low recent minutes (184 mins in last 5) combined with high per-90 rate ($0.704$) illustrates why sample-size weighted shrinkage is critical.
4. **William Osula (Newcastle, 2,740 DB mins)**:
   - Career $xG/90 = 0.316$, Last 5 Mins = 39 mins (0 starts).
   - *Finding*: Recency minutes model correctly identifies 0 recent starts, suppressing expected minutes from 82.1 down to realistic rotation levels (<20 mins).
5. **Beto (Everton, 760 DB mins)**:
   - Career $xG/90 = 0.580$, Last 5 Mins = 120 mins (1 start).
   - *Finding*: Recency role features properly discount per-90 rates when recent starting role is non-established.

---

## 5. Verification & Testing

- **Frontend Integration**: Added `"TEMPORAL & CURRENT-FORM AUDIT"` card in [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html) with `DIAGNOSTIC ONLY — DOES NOT AFFECT PROJECTIONS` badge.
- **Regression Tests**: Added 5 unit tests in `tests/test_phase3c7_temporal_recency_audit.py` (**5/5 passed**).
- **Full Test Suite**: Tested cleanly across repo (**77/77 tests passed**).
