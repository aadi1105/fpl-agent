# 2026/27 Player-Price Data Integrity Audit

## 1. Executive Summary

* **Status**: `COMPLETED & VERIFIED`
* **Objective**: Perform a comprehensive, cross-layer price integrity audit for all 590 active 2026/27 FPL players across Database, Projection Engine, Optimizer, Positional Diagnostics, API, and Frontend.

---

## 2. Authoritative Price Source & Data Flow

1. **Ingestion Layer**: Ingests official FPL `bootstrap-static` JSON endpoint into `Player.now_cost` in `backend/ingestion/fpl_api.py`.
2. **Database Representation**: Stored in `Player.now_cost` (`Integer`) as **tenths** (e.g. `80` = £8.0m, `155` = £15.5m).
3. **Canonical Conversion**:
   - `now_cost` (Integer Tenths): `80`
   - `price` / `now_cost_str` (Float Millions / String): `8.0` / `"£8.0m"`.
4. **Projection Layer**: `ProjectionEngine` accesses `player.now_cost / 10.0` for ML predictors (`xg_v1_lgbm`, `xa_v1_lgbm`, `expected_minutes_v1`).
5. **Optimizer Layer**: `SquadOptimizer` accesses `p.now_cost` for MILP budget constraint ($\sum p.\text{now\_cost} \le 1000$) and returns `now_cost_str` (`"£8.0m"`).
6. **Positional Diagnostics**: Computes dynamic `pos_price_percentile` relative to players in the same `element_type` using `now_cost / 10.0`.
7. **Frontend**: Displays `now_cost_str` across pitch, table, modal, and optimizer output.

---

## 3. Reconciliation Results Across All 590 Players

| Metric | Count / Value | Percentage | Status |
| :--- | :---: | :---: | :--- |
| **Total Active Players Audited** | **590** | **100.0%** | `AUDITED` |
| **Matching Prices Across All Layers** | **590** | **100.0%** | `VERIFIED` |
| **Mismatched Prices** | **0** | **0.0%** | `NONE` |
| **Stale Records** | **0** | **0.0%** | `NONE` |
| **Missing Prices** | **0** | **0.0%** | `NONE` |

---

## 4. Key Representative Player Verification

| Player | Position | Club | DB Tenths (`now_cost`) | DB Price (£m) | Projection Engine Price | Optimizer Output | Display UI | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gabriel** | DEF | ARS | **80** | **£8.0m** | **£8.0m** | **£8.0m** | **£8.0m** | **MATCH** |
| **Raya** | GKP | ARS | **60** | **£6.0m** | **£6.0m** | **£6.0m** | **£6.0m** | **MATCH** |
| **Igor Jesus** | FWD | NFO | **60** | **£6.0m** | **£6.0m** | **£6.0m** | **£6.0m** | **MATCH** |
| **Erling Haaland** | FWD | MCI | **155** | **£15.5m** | **£15.5m** | **£15.5m** | **£15.5m** | **MATCH** |

---

## 5. Positional Price Distribution

| Position | Player Count | Min Price | Max Price | Median Price | Mean Price |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **GKP** | 66 | £4.0m (40) | £6.0m (60) | £4.5m | £4.54m |
| **DEF** | 194 | £4.0m (40) | £8.0m (80) | £4.5m | £4.71m |
| **MID** | 260 | £4.5m (45) | £12.0m (120) | £5.5m | £5.53m |
| **FWD** | 70 | £4.5m (45) | £15.5m (155) | £5.5m | £5.81m |

---

## 6. Test Suite & Regression Verification

- Created [`tests/test_price_integrity.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_price_integrity.py) with 6 comprehensive test cases.
- Ran `python -m pytest`: **6 / 6 price integrity tests passed (100%)**.
- Ran full test suite: **57 / 57 total tests passed (100%)**.
- Pushed commit `1a4e23d` to GitHub (`main -> main`).
