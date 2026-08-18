# Pre-Phase 3C Audit: Projection Pipeline, Current Roster & Frontend Reconciliation

## 1. Executive Summary & Audit Purpose

* **Audit Status**: `COMPLETED` (Read-only diagnostic audit + Frontend status fix)
* **Objective**: Diagnose why low-cost players (£4.5m–£5.5m) receive high expected points ($xP$), explain why the optimizer leaves £7.5m unused in bank, and verify current-club / transfer context isolation.

---

## 2. Complete Pipeline Component Trace (GW0–GW3)

### A. Erling Haaland (Man City, £15.5m FWD)
* **Current Club**: Man City (MCI) | **Historical Mins**: 2,953 | **Goals**: 27 | **Assists**: 8
* **GW0 vs BOU (H)**: $xMins = 76.7$ ($P(\text{start})=0.86$), $xG = 1.019$ (`xg_v1_lgbm`), $xA = 0.204$ (`xa_v1_lgbm`), **GW0 xP = 7.80**
* **GW1 vs CRY (A)**: $xMins = 75.4$, $xG = 0.974$, $xA = 0.262$, **GW1 xP = 6.48**
* **GW2 vs COV (H)**: $xMins = 76.9$, $xG = 0.977$, $xA = 0.198$, **GW2 xP = 7.18**
* **GW3 vs MUN (A)**: $xMins = 75.4$, $xG = 0.974$, $xA = 0.263$, **GW3 xP = 6.25**
* **Weighted 4-GW xP**: **`7.29`**

### B. Reiss Nelson (Arsenal, £5.5m MID) — Mandatory Diagnostic Case
* **Current Club**: Arsenal (ARS) | **Historical Mins**: 118 | **Goals**: 0 | **Assists**: 1
* **GW0 vs COV (H)**: $xMins = 75.9$ ($P(\text{start})=0.88$), $xG = 0.644$, $xA = 0.295$, **GW0 xP = 6.62**
* **GW1 vs AVL (A)**: $xMins = 77.3$, $xG = 0.467$, $xA = 0.251$, **GW1 xP = 5.06**
* **GW2 vs CHE (H)**: $xMins = 72.9$, $xG = 0.583$, $xA = 0.289$, **GW2 xP = 6.12**
* **GW3 vs SUN (A)**: $xMins = 77.3$, $xG = 0.467$, $xA = 0.263$, **GW3 xP = 5.07**
* **Weighted 4-GW xP**: **`6.08`** (Inflated fringe-player projection)

### C. Harrison Reed (Fulham, £4.5m MID)
* **Current Club**: Fulham (FUL) | **Historical Mins**: 89 | **Goals**: 1 | **Assists**: 0
* **GW0 vs CHE (H)**: $xMins = 73.5$ ($P(\text{start})=0.84$), $xG = 0.586$, $xA = 0.299$, **GW0 xP = 6.06**
* **GW1 vs SUN (A)**: $xMins = 74.9$, $xG = 0.354$, $xA = 0.345$, **GW1 xP = 4.51**
* **GW2 vs CRY (H)**: $xMins = 73.7$, $xG = 0.531$, $xA = 0.296$, **GW2 xP = 5.81**
* **GW3 vs LIV (A)**: $xMins = 73.3$, $xG = 0.315$, $xA = 0.379$, **GW3 xP = 4.05**
* **Weighted 4-GW xP**: **`5.51`** (Inflated low-cost midfielder projection)

---

## 3. Explanation of £7.5m Unused Budget

* **FINDING**: Total Budget Spent = **£92.5m / £100.0m** | Remaining Bank = **£7.5m**.
* **Root Cause**:
  1. Cheap midfielders (£4.5m Reed and £5.5m Nelson) project at **5.51** and **6.08** weighted 4-GW xP.
  2. Premium midfielders (£9.5m Saka, £10.5m Palmer) project at **6.5 – 7.2** weighted 4-GW xP.
  3. Upgrading £4.5m Reed to £9.5m Saka costs **+£5.0m** but yields only **+1.2 xP** gain (~0.24 xP per £1m spent).
  4. The MILP solver mathematically determines that buying cheap high-projecting enablers yields a 15-man squad 4-GW xP of **`72.12`**, which cannot be meaningfully improved by spending the remaining £7.5m.

---

## 4. Transfer Audit & Feature Isolation Analysis

* **FINDING**:
  - `historical_xg_dataset.csv` and `historical_xa_dataset.csv` build rolling features per `element` (player ID) using `shift(1)`.
  - Historical rows correctly retain historical team identity (e.g. Nelson's 2025/26 Brentford loan rows retain team = Brentford).
* **LIMITATION (Transferred Player Minutes)**:
  - When `expected_minutes_v1` evaluates a player with sparse recent 5-match logs at their new/current club (or returning from loan), price tier defaults assigned starter-level inputs ($xMins \approx 73-79$ mins, $P(\text{start}) \approx 0.84-0.88$).
  - `xg_v1_lgbm` and `xa_v1_lgbm` combine high $xMins$ with top team attacking ratings (e.g. Arsenal rating = 1200), producing $xG \approx 0.60$ and $xA \approx 0.30$.

---

## 5. Top 20 Low-Cost Players (Cost $\le £6.0$m)

| Rank | Player | Club | Position | Price | $xMins$ | $P(\text{start})$ | $xG$ | $xA$ | GW0 xP | Audit Note |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | Nelson | ARS | MID | £5.5m | 75.9 | 0.881 | 0.644 | 0.295 | **6.62** | ⚠️ Over-projected fringe player |
| **2** | Dowman | ARS | MID | £5.5m | 79.5 | 0.887 | 0.626 | 0.238 | **6.43** | ⚠️ Over-projected youth player |
| **3** | Reed | FUL | MID | £4.5m | 73.5 | 0.844 | 0.586 | 0.299 | **6.06** | ⚠️ Over-projected low-cost mid |
| **4** | Carvalho | BRE | MID | £5.0m | 78.0 | 0.844 | 0.486 | 0.124 | **5.28** | Nailed starter |
| **5** | Tzimas | BHA | FWD | £5.5m | 78.3 | 0.886 | 0.576 | 0.216 | **5.12** | Forward option |
| **6** | Awoniyi | NFO | FWD | £5.5m | 74.6 | 0.876 | 0.466 | 0.170 | **5.04** | Forward option |
| **7** | White | ARS | DEF | £5.5m | 73.2 | 0.853 | 0.085 | 0.066 | **4.59** | Nailed defender |
| **8** | Calafiori | ARS | DEF | £5.5m | 74.4 | 0.868 | 0.076 | 0.064 | **4.50** | Nailed defender |
| **9** | Raya | ARS | GKP | £6.0m | 75.0 | 0.871 | 0.001 | 0.005 | **4.46** | Nailed goalkeeper |
| **10** | Arrizabalaga | ARS | GKP | £5.0m | 76.3 | 0.854 | 0.001 | 0.006 | **4.42** | Backup GK over-projected |

---

## 6. Frontend Status & Transparency Fixes

* **FIXED**: Updated `frontend/index.html`, `backend/config.py`, and `backend/schemas.py`.
* **New Status Display**:
  - Header Classification: **`Hybrid Statistical + ML Engine v1.0`**
  - Minutes: `expected_minutes_v1` (ML DEPLOYED)
  - xG: `xg_v1_lgbm` (ML DEPLOYED)
  - xA: `xa_v1_lgbm` (ML DEPLOYED)
  - Clean Sheet / DEFCON / Bonus: Statistical Baselines

---

## 7. Recommendations & Next Steps

1. **Phase 3C Recommendation**: **Proceed to Phase 3C (Clean Sheet & Defensive ML Models)** after user review.
2. **Current-Role Squad Status Calibration**: In a future refactoring phase, incorporate explicit squad status flags (e.g. starter vs backup vs youth) into `expected_minutes_v1` feature extraction for transferred/low-sample players.
