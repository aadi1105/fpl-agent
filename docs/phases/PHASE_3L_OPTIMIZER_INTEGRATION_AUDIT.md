# PHASE 3L — OPTIMIZER INTEGRATION & PROJECTION CONSUMPTION AUDIT REPORT

**Date**: 2026-08-26  
**Status**: `COMPLETED & EMPIRICALLY VERIFIED (INTEGRATION AUDIT)`  
**Data Flow Verified**: `expected_xp_calibrated_v2.json -> ProjectionEngine -> PlayerProjection DB -> MILP SquadOptimizer`  
**Optimizer Status**: `FROZEN & VERIFIED (Zero model changes, zero squad recommendations made)`  
**Final Safety Gate Verdict**: **`SAFE TO PROCEED TO 3M`**  

---

## 1. Trace of Complete Data Flow

1. **Calibration Layer Artifact**:
   - `backend/ml/models/expected_xp_calibrated_v2.json` contains the Model D piecewise price-tier and role-aware calibration multipliers.
2. **Projection Engine**:
   - `backend/projections/engine.py` loads `expected_xp_calibrated_v2.json` in `__init__`.
   - `calculate_player_xp_breakdown()` computes `cal_xg` and `cal_xa` using Model D multipliers and returns `total_xp = calibrated_xp`.
3. **Database Storage**:
   - `run_projections(start_gw=1, end_gw=4, source="internal")` saves fixture-specific `total_xp` into `PlayerProjection.expected_points` in the SQLite database (2,396 projection records synchronized across GW1-4).
4. **MILP Squad Optimizer**:
   - `backend/optimizer/squad_optimizer.py` queries `PlayerProjection.expected_points` for `source="internal"` across GW1-4.
   - Calculates `player_weighted_xp` using horizon weights (`[0.55, 0.20, 0.15, 0.10]`).
   - MILP Solver (`pywraplp.Solver.CreateSolver('CBC')`) sets `player_weighted_xp` as the objective coefficient:
     $$\text{Maximize } \sum_{i=1}^{N} \text{player\_weighted\_xp}_i \cdot x_i$$

---

## 2. Proof of xP Version Consumption (Diagnostic Player Pool)

For the diagnostic player set, we compared Raw xP, Phase 3H (v1) xP, Phase 3K (v2) xP, and the actual `PlayerProjection.expected_points` passed into the optimizer:

| Player Name | Position | Cost | GW1 Fixture | Raw xP | Phase 3H xP | Phase 3K (v2) xP | Optimizer Input Value | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Erling Haaland** | FWD | £15.5m | BOU (H) | 4.22 | 6.53 | **5.90** | **5.90** | **MATCH** |
| **Bruno Fernandes**| MID | £12.0m | HUL (A) | 4.10 | 5.64 | **5.62** | **5.62** | **MATCH** |
| **Bukayo Saka** | MID | £9.5m | COV (H) | 4.51 | 4.31 | **5.48** | **5.48** | **MATCH** |
| **Cole Palmer** | MID | £9.5m | FUL (A) | 3.77 | 3.74 | **4.93** | **4.93** | **MATCH** |
| **Omar Marmoush** | FWD | £7.0m | BOU (H) | 3.46 | 3.52 | **4.27** | **4.27** | **MATCH** |
| **Nico O'Reilly** | DEF | £6.5m | BOU (H) | 5.30 | 4.51 | **4.50** | **4.50** | **MATCH** |
| **Riccardo Calafiori**| DEF | £5.5m | COV (H) | 5.88 | 3.89 | **3.90** | **3.90** | **MATCH** |
| **João Pedro** | FWD | £7.5m | FUL (A) | 3.24 | 3.20 | **3.87** | **3.87** | **MATCH** |
| **Dominic Calvert-Lewin**| FWD| £6.0m | NFO (A) | 2.87 | 3.17 | **3.59** | **3.59** | **MATCH** |
| **Phil Foden** | MID | £7.0m | BOU (H) | 4.34 | 4.28 | **4.77** | **4.77** | **MATCH** |
| **David Raya** | GKP | £6.0m | COV (H) | 5.56 | 3.44 | **3.44** | **3.44** | **MATCH** |
| **Gabriel Magalhães**| DEF | £8.0m | COV (H) | 5.59 | 3.42 | **3.42** | **3.42** | **MATCH** |

**Verification Outcome**: 100% of diagnostic players match `expected_xp_calibrated_v2` projections EXACTLY.

---

## 3. Structural, Price & Transfer Integrity Audit

1. **Price Integrity**:
   - `Player.now_cost` integer cost used throughout (e.g. 155 = £15.5m).
   - Total budget constraint enforced at 1000 integer units (£100.0m).
2. **Squad Structural Constraints**:
   - 15 total squad players (2 GKP, 5 DEF, 5 MID, 3 FWD).
   - Max 3 players per Premier League club strictly enforced by linear constraint:
     $$\sum_{i \in \text{Club}_k} x_i \le 3, \quad \forall k \in \{1 \dots 20\}$$
3. **Current Club & Transfer Integrity**:
   - Verified transferred players (Awoniyi at Coventry, Nelson at Arsenal, Smith Rowe at Fulham, Solanke at Spurs, Neto at Chelsea) reflect 2026/27 clubs, prices, and fixtures.
4. **Objective Value Reconciliation**:
   - Manual sum of selected squad 4-GW weighted xP = **64.85**
   - MILP Solver Objective Value = **64.85**
   - **Discrepancy = 0.0000 pts** (`PERFECTLY RECONCILED`).
5. **Full-Pool Consistency**:
   - Audited all 599 active 2026/27 players: 0 missing v2 xP, 0 missing price, 0 missing club, 0 missing position, 0 missing fixture (`100% COMPLETE`).
6. **Hidden Heuristics Audit**:
   - Inspected `backend/optimizer/squad_optimizer.py`. **Zero manual player boosts, penalties, ownership, or consensus adjustments exist.**

---

## 4. Controlled Diagnostic Optimization (Run C Output)

*(Diagnostic experiment only for verification; NOT a squad recommendation)*

* **Squad Cost**: £100.0m | **Remaining Bank**: £0.0m | **Objective Value**: 64.85 weighted xP
* **Captain**: Bruno Fernandes (5.62 GW1 xP) | **Vice Captain**: Bukayo Saka (5.48 GW1 xP)
* **Starting XI (3-5-2)**:
  - GKP: Petrović (£4.5m, 3.66 xP)
  - DEF: O'Reilly (£6.5m, 4.50 xP), Gvardiol (£5.5m, 4.01 xP), De Cuyper (£4.5m, 3.97 xP)
  - MID: Bruno Fernandes (£12.0m, 5.62 xP), Bukayo Saka (£9.5m, 5.48 xP), Rayan Cherki (£7.5m, 5.19 xP), Bryan Mbeumo (£8.0m, 4.64 xP), Ouattara Dango (£6.5m, 4.58 xP)
  - FWD: Hugo Ekitiké (£7.5m, 4.26 xP), Yoane Wissa (£6.0m, 4.02 xP)
* **Bench**: Leno (GKP, £4.5m, 3.64 xP), J.Timber (DEF, £6.5m, 3.96 xP), Calafiori (DEF, £5.5m, 3.90 xP), Nmecha (FWD, £5.5m, 3.88 xP)

---

## 5. Final Safety Gate & Verdict

| Safety Gate Question | Audit Finding | Status |
| :--- | :--- | :---: |
| 1. Is optimizer consuming `expected_xp_calibrated_v2`? | YES (100% exact match across all diagnostic players) | **PASS** |
| 2. Is optimizer objective maximizing expected FPL points? | YES (Maximizes 4-GW weighted sum of xP) | **PASS** |
| 3. Are current prices being used? | YES (Player.now_cost in integer £0.1m units) | **PASS** |
| 4. Are current clubs being used? | YES (Official 2026/27 team assignments) | **PASS** |
| 5. Are current fixtures represented? | YES (GW1-4 official 2026/27 fixtures) | **PASS** |
| 6. Are current positions being used? | YES (Canonical element_type) | **PASS** |
| 7. Are budget constraints correct? | YES (Total cost $\le$ 1000 units = £100.0m) | **PASS** |
| 8. Are squad structure constraints correct? | YES (2 GKP, 5 DEF, 5 MID, 3 FWD) | **PASS** |
| 9. Is max-3-per-club enforced? | YES (OR-Tools linear constraint enforced) | **PASS** |
| 10. Is captaincy using intended projection? | YES (Highest GW1 xP in starting XI) | **PASS** |
| 11. Is bench logic using intended projection? | YES (Starting XI maximized, bench ordered by xP) | **PASS** |
| 12. Are there hidden player-specific heuristics? | NO (Zero manual boosts/penalties/ownership/consensus) | **PASS** |
| 13. Does optimizer objective reconcile with selected xP? | YES (0.0000 pts discrepancy) | **PASS** |
| 14. Does v2 optimizer output differ explainably from v1? | YES (Reflects mid-price attacker calibration adjustments) | **PASS** |
| 15. Is optimizer safe to use for actual GW1 squad? | YES | **PASS** |

### **`FINAL VERDICT: SAFE TO PROCEED TO 3M`**

---

## 6. Stop Condition Confirmation

* **Phase 3L Audit**: `COMPLETED`
* **Optimizer Modified**: `NO (Read-only integration audit)`
* **Projections Modified**: `NO`
* **Final GW1 Squad Recommended**: `NO (Awaiting explicit user direction for Phase 3M)`
