# Phase 3C — Clean Sheet & Defensive ML Models (`cs_v1_lgbm` & `defcon_v1_poisson`)

## 1. Executive Summary

* **Status**: `COMPLETED & DEPLOYED`
* **Objective**: Build, evaluate, and integrate leak-free historical models for Clean Sheet probability ($P(\text{clean\_sheet})$) and Defensive Contribution ($P(\text{DEFCON})$) under 2026/27 FPL rules.
* **Key Deployment Decisions**:
  - **Clean Sheet Model (`cs_v1_lgbm`)**: **DEPLOYED ML**. Outperformed baseline heuristic on 2025/26 out-of-sample test set (LogLoss `0.6549` vs `0.6658` — **+1.63% improvement**, Brier score `0.2314` vs `0.2361`, ROC-AUC `0.5665` vs `0.5448`).
  - **DEFCON Model (`defcon_v1_poisson`)**: **HYBRID POISSON DEPLOYED**. Due to extreme class imbalance (~3.5% event frequency), LightGBM suffered LogLoss degradation. The 2026/27 Poisson model (10 CBIT for DEF, 12 CBIRT for MID/FWD, +2 FPL points capped) demonstrated superior out-of-sample logloss calibration (`1.1691` vs `1.8861`) and was deployed per Section 14 criteria.

---

## 2. 2026/27 Scoring Engine & Mathematical Formulations

### 1. Clean Sheet Probability & Scoring
- **Model**: `cs_v1_lgbm` LightGBM probabilistic classifier.
- **Points Awarded**:
  - Goalkeepers (GKP): 4.0 points (if played $\ge 60$ mins).
  - Defenders (DEF): 4.0 points (if played $\ge 60$ mins).
  - Midfielders (MID): 1.0 point (if played $\ge 60$ mins).
  - Forwards (FWD): 0.0 points.
- **Expected Value Equation**:
  $$\text{Expected CS Points} = P(\text{clean\_sheet}) \times \text{CS Points} \times \frac{\text{xMins}}{90.0}$$

### 2. Defensive Contribution (DEFCON)
- **Model**: `defcon_v1_poisson` (Poisson CDF with position-specific thresholds).
- **Thresholds**:
  - Defenders (DEF): $\ge 10$ Clearances, Blocks, Interceptions, Tackles (CBIT).
  - Midfielders/Forwards (MID/FWD): $\ge 12$ Clearances, Blocks, Interceptions, Tackles, Recoveries (CBIRT).
- **Points Awarded**: Single +2 FPL points award (capped at +2 per match).
- **Expected Value Equation**:
  $$\text{Expected DEFCON Points} = P(\text{DEFCON}) \times 2.0 \times \frac{\text{xMins}}{90.0}$$

---

## 3. Empirical Out-of-Sample Model Evaluation (2025/26 Test Set)

### 1. Clean Sheet Model Evaluation

| Model Variant | LogLoss | Brier Score | ROC-AUC | Decision |
| :--- | :---: | :---: | :---: | :--- |
| **Baseline Heuristic** | 0.6658 | 0.2361 | 0.5448 | Replaced |
| **LightGBM (`cs_v1_lgbm`)** | **0.6549** | **0.2314** | **0.5665** | **DEPLOYED (ML)** |

### 2. DEFCON Model Evaluation

| Model Variant | LogLoss | Brier Score | ROC-AUC | Decision |
| :--- | :---: | :---: | :---: | :--- |
| **Baseline Poisson (`defcon_v1_poisson`)** | **1.1691** | **0.0502** | **0.6324** | **DEPLOYED (HYBRID)** |
| **LightGBM Classifier** | 1.8861 | 0.0546 | 0.5000 | Retained Baseline |

---

## 4. Double Gameweek & Transfer Integrity

- **Double Gameweek (DGW)**: Fixture A and Fixture B are evaluated independently ($P(\text{CS}_A)$ and $P(\text{CS}_B)$), and expected points are summed without aggregating fixture stats prior to prediction.
- **Transfers / Low-Sample**: Uses shrinkage to baseline defaults ($0.30$ clean sheet rate, $4.0$ cbit90) for low-sample players.

---

## 5. Test Suite & Verification

- Created [`tests/test_phase3c_cs_defcon.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3c_cs_defcon.py) (5 test cases).
- Ran full test suite: **62 / 62 total test cases passed (100%)**.
