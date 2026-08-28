# PHASE 3N.14 REPORT

## A. Expected Points Audit

### Pipeline:
- `player status` $\to$ `MinutesPredictor` (76.2 xMins) $\to$ `XGPredictor` (0.485 xG) $\to$ `XAPredictor` (0.157 xA) $\to$ `CSPredictor` / `DEFCONPredictor` $\to$ `ProjectionEngine` component breakdown $\to$ `expected_xp_calibrated_v2.json` piecewise calibration $\to$ `SquadOptimizer`.

### Calibration:
- Piecewise Model D + Role Active Calibration (`expected_xp_calibrated_v2.json`).
- Evaluates individual expected value buckets rather than applying uniform position multipliers. Adjustments scale continuously based on player baseline metrics.

### Historical FPL data usage:
- Historical start counts, minutes, appearance weights, and per-90 metrics directly inform LightGBM feature vectors and baseline shrinkage.

### Distribution:
- **Total Eligible Players**: 612
- $xP \ge 6.0$: 3 players (Bruno 6.92, Isak 6.58, Haaland 6.30)
- $xP \ge 5.0$: 4 players (Palmer 5.53)
- $xP \ge 4.0$: 9 players
- $xP \ge 3.0$: 41 players
- **Positional Max xP**: MID (6.92), FWD (6.58), GKP (3.52), DEF (3.02)
- **Mean Pool xP**: 0.97 | **Median Pool xP**: 0.70

### Premium-player findings:
- **Haaland (£15.5m)**: GW2 xP = 6.30 (76.2 xMins, 0.485 xG, 0.157 xA, +2.05 calib delta).
  - *Value Metric*: $6.30 / 15.5 = \mathbf{0.41 \text{ xP/£m}}$.
- **Bruno Fernandes (£12.0m)**: GW2 xP = 6.92 (77.1 xMins, 0.328 xG, 0.156 xA, 5 pts/goal + CS bonus).
  - *Value Metric*: $6.92 / 12.0 = \mathbf{0.58 \text{ xP/£m}}$.

### Model verdict:
**`A. WELL CALIBRATED & MATHEMATICALLY SOUND`**

---

## B. Optimizer

- **Medium-Term horizon score**: **54.99 pts**
- **Top player contributions**:
  - Isak (FWD, £9.0m): 5.91 weighted xP
  - Palmer (MID, £9.5m): 5.01 weighted xP
  - Saka (MID, £9.5m): 4.82 weighted xP
  - Mbeumo (MID, £8.0m): 4.31 weighted xP
  - João Pedro (FWD, £7.5m): 4.01 weighted xP
- **Reason Haaland is/isn't selected**:
  Haaland yields 6.30 xP, but costs £15.5m (0.41 xP/£m). Selecting Haaland forces downgrading two £9.0m/£9.5m premium starters to £4.5m benchwarmers, losing 3.5+ net points across the squad. The MILP solver rationally excludes Haaland to maximize total squad points.
- **Any model changes**: NONE (ML models & optimizer parameters 100% untouched).

---

## C. UI Redesign

- **Major changes**: Complete visual and structural overhaul into a **Dark Stadium / Broadcast Football Analytics Command Center**.
- **New visual system**: Deep stadium charcoal `#0B0E14`, glassmorphism borders, Pitch Neon Green `#00FF87`, Electric Cyan `#00D2FF`, and position color badges.
- **Optimizer**: Hero Broadcast Scoreboard module, 1-Click Solve action, and dynamic metric cards.
- **My Team**: Command Center team management page with team rating, bank, FTs, chips, direct starter/bench substitutions, and legal transfer solver.
- **Diagnostics**: Mode-aware horizon panel with position filtering tabs (`ALL | GKP | DEF | MID | FWD`).
- **Responsive**: Fully responsive across desktop (1440px+), laptop (1280px), tablet, and mobile.

---

## D. Verification

- **Existing tests**: 80 / 80
- **New tests**: 4 / 4 in [`tests/test_phase3n14_model_audit_and_ui.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n14_model_audit_and_ui.py)
- **Browser verification**: **PASS**

---

## E. Final Verdict

**MODEL**: **`VERIFIED`**  
**UI**: **`VERIFIED`**
