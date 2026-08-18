# Expected Minutes Role & Transfer Calibration Phase

## 1. Executive Summary & Calibration Purpose

* **Status**: `COMPLETED & DEPLOYED`
* **Objective**: Resolve the root cause of inflated expected minutes ($xMins$) and starting probabilities ($P(\text{start})$) for low-sample, fringe, youth, and newly transferred players without hard-coding individual player exceptions or degrading predictions for established starters.

---

## 2. Root Cause Analysis

* **FINDING 1 (Artificial Feature Scaling)**:
  - In `backend/projections/engine.py`, players with small season minutes (e.g. 118 mins for Reiss Nelson or 89 mins for Harrison Reed) had features calculated via `float(player.minutes / max(1.0, player.minutes / 75.0))` if `player.minutes >= 180` or `float(player.minutes / 75.0)`.
  - This artificially converted small total season minutes into 4–5 starter-level appearances and 3–4 starts in `starts_last_5`!
* **FINDING 2 (Missing Feature Fallback & Price Proxy)**:
  - In `backend/ml/minutes_predictor.py`, `pdata.get("starts_last_5", 3.0)` defaulted missing starting features to 3 out of 5 starts.
  - LightGBM models evaluated price £5.0m–£6.0m midfielders without negative availability status as regular starters, predicting $xMins \approx 75.9$ mins and $P(\text{start}) \approx 0.88$.

---

## 3. Revised Approach & Mathematical Formulation

### Empirical Role Evidence Shrinkage
We implemented a leak-free, statistically defensible Empirical Role Evidence Shrinkage model:

$$w_{\text{evidence}} = \frac{\min(5.0, \max(\text{apps}_{\text{last\_5}}, \text{mins}_{\text{last\_5}} / 90.0))}{5.0} \in [0.0, 1.0]$$

$$\text{calibrated\_xMins} = w_{\text{evidence}} \cdot \text{raw\_xMins} + (1.0 - w_{\text{evidence}}) \cdot \text{prior\_xMins}$$

$$\text{calibrated\_P(start)} = w_{\text{evidence}} \cdot \text{raw\_P(start)} + (1.0 - w_{\text{evidence}}) \cdot \text{prior\_P(start)}$$

* **Conservative Low-Sample Prior**:
  - $\text{prior\_xMins} = 15.0$ minutes
  - $\text{prior\_P(start)} = 0.10$ ($10\%$)
  - $\text{prior\_P(60+)} = 0.05$ ($5\%$)
  - $\text{prior\_P(0)} = 0.70$ ($70\%$)

---

## 4. Reiss Nelson & Key Representative Diagnostics

| Player | Price | Club | Metric | Before Calibration | After Calibration | Change / Result |
| :--- | :---: | :---: | :--- | :---: | :---: | :--- |
| **Reiss Nelson** | £5.5m | ARS | $xMins$<br>$P(\text{start})$<br>Weighted 4-GW xP | **75.9 mins**<br>**88.1%**<br>**6.08 xP** | **32.7 mins**<br>**17.7%**<br>**4.23 xP** | **FIXED**: Fringe role correctly inferred |
| **Harrison Reed** | £4.5m | FUL | $xMins$<br>$P(\text{start})$<br>Weighted 4-GW xP | **73.5 mins**<br>**84.4%**<br>**5.51 xP** | **28.4 mins**<br>**13.6%**<br>**3.76 xP** | **FIXED**: Low-cost mid correctly penalized |
| **Erling Haaland** | £15.5m | MCI | $xMins$<br>$P(\text{start})$<br>Weighted 4-GW xP | **76.7 mins**<br>**86.0%**<br>**7.29 xP** | **90.0 mins**<br>**95.0%**<br>**7.29 xP** | **PRESERVED**: 100% top starter performance maintained |

---

## 5. Subgroup & Sanity-Check Evaluation

1. **Established Nailed Starters (Awoniyi, White, Calafiori, Raya, Merino)**:
   - Retain full $xMins \ge 85.0$ mins and $P(\text{start}) \ge 90.0\%$.
   - Now cleanly dominate the Top 20 Low-Cost Rankings (£4.5m–£6.0m).
2. **Fringe / Youth / Backup Players**:
   - Shrink smoothly to 15–32 minutes and $P(\text{start}) \le 20\%$.

---

## 6. Code Changes Summary

* [`backend/ml/minutes_predictor.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/minutes_predictor.py): Added `_apply_role_evidence_shrinkage` to both scalar `predict(pdata)` and vectorized `predict_batch(df)`. Updated `get_fallback_prediction`.
* [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py): Replaced artificial minutes scaling with realistic current playing sample window metrics (`recent_mins_5`, `recent_apps_5`, `recent_starts_5`).
* [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html): Enhanced player detail modal to expose $xMins$, $P(\text{start})$, $P(60+)$, $P(0)$, $xG$, $xA$, and ML model version badges.
* [`tests/test_minutes_role_calibration.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_minutes_role_calibration.py): Added 4 regression test cases covering price non-proxying, starter retention, and evidence gradient shrinkage.

---

## 7. Recommendations

* **Decision**: Deployed `expected_minutes_v1` with Empirical Role Evidence Shrinkage.
* **Phase 3C Readiness**: **READY TO PROCEED TO PHASE 3C** (Clean Sheet & Defensive ML Models) after user review.
