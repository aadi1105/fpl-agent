# Optimizer Modes, Progress Tracking & Positional Value Audit

## 1. Executive Summary

* **Status**: `COMPLETED & DEPLOYED`
* **Objective**:
  1. Fix the collapse of optimization modes so that each mode (`CURRENT_GW_PLUS_3`, `STRONG_XI_DUMP_BENCH`, `BALANCED_BENCH`, `MAXIMUM_SQUAD`) evaluates a distinct mathematical MILP problem.
  2. Implement an asynchronous 10-stage background progress tracking system for long-running optimization jobs (`POST /api/v1/optimize/job`, `GET /api/v1/optimize/status/{job_id}`).
  3. Implement position-relative percentiles (`pos_price_percentile`, `pos_xp_percentile`, `pos_value_percentile`) so £6.0m GKP vs £6.0m DEF vs £6.0m FWD are evaluated strictly relative to their positional peers.
  4. Expose real-time progress UI and a side-by-side Mode Comparison tool in the frontend.

---

## 2. Root Cause Analysis of Mode Collapse

* **FINDING 1 (`BALANCED_BENCH` Fallback)**:
  - In `backend/optimizer/squad_optimizer.py`, `BALANCED_BENCH` was not explicitly handled in the `if/elif` block. It defaulted to `DEFAULT_HORIZON_WEIGHTS` (`[0.55, 0.20, 0.15, 0.10]`), rendering its weights identical to `CURRENT_GW_PLUS_3`.
* **FINDING 2 (Insignificant Bench Penalty)**:
  - `STRONG_XI_DUMP_BENCH` previously applied a tiny cost penalty (`0.005 * now_cost`), which was too small relative to total player xP to shift the MILP solution away from `CURRENT_GW_PLUS_3`.
* **FINDING 3 (Over-projected Cheap Enablers Pre-Calibration)**:
  - Prior to the role evidence shrinkage calibration, cheap enablers (£4.5m Reed, £5.5m Nelson) were projected at starter-level xP (~5.5–6.0 xP), creating a math constraint bottleneck where all modes selected the exact same cheap players.

---

## 3. Mathematical Formulations of the 4 Modes

1. **`CURRENT_GW_PLUS_3`** (Standard Horizon):
   - Horizon weights: $[0.55, 0.20, 0.15, 0.10]$.
   - Maximize: $\sum_{i \in \text{Squad}} \text{weighted\_4gw\_xp}_i$.
2. **`STRONG_XI_DUMP_BENCH`** (Starting XI Concentration):
   - Horizon weights: $[0.70, 0.15, 0.10, 0.05]$ (heavy GW0/GW1 focus).
   - Maximize: $\sum_{i \in \text{Squad}} (\text{weighted\_4gw\_xp}_i - 0.025 \cdot \text{price\_in\_m}_i)$ to force bench budget into minimum £4.0m/£4.5m enablers.
3. **`BALANCED_BENCH`** (Squad Minutes Security):
   - Horizon weights: $[0.45, 0.25, 0.15, 0.15]$.
   - Maximize: $\sum_{i \in \text{Squad}} (\text{weighted\_4gw\_xp}_i + 0.015 \cdot \min(450, \text{mins}_i))$ to incentivize reliable minutes security across all 15 squad slots.
4. **`MAXIMUM_SQUAD`** (Equal 4-GW Horizon):
   - Horizon weights: $[0.25, 0.25, 0.25, 0.25]$.
   - Maximize: Unweighted 4-GW total squad xP.

---

## 4. Empirical 4-Mode Side-by-Side Comparison (Exact Same Snapshot)

| Mode | Budget / Bank | GW0 XI xP | GW0 Total xP | 4-GW Score | Captain | Starting XI Highlights | Bench Highlights |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| **`CURRENT_GW_PLUS_3`** | £100.0m / £0.0m | 62.43 | 70.67 | 76.75 | Haaland | Kelleher, Timber, White, Calafiori, Frimpong, Semenyo, Gibbs-White, Foden, Haaland, Awoniyi, Osula | Verbruggen, Hickey, Sarr, Okafor |
| **`STRONG_XI_DUMP_BENCH`** | £100.0m / £0.0m | 62.43 | 70.67 | **77.75** | Haaland | Kelleher, Timber, White, Calafiori, Frimpong, Semenyo, Gibbs-White, Foden, Haaland, Awoniyi, Osula | Verbruggen, **James, Sarr, Gnonto** (Swaps bench enablers) |
| **`BALANCED_BENCH`** | £100.0m / £0.0m | 61.16 | 69.40 | 76.18 | Haaland | Kelleher, Timber, White, Calafiori, Frimpong, **James, Semenyo, Doku**, Haaland, Awoniyi, Osula | Verbruggen, Sarr, Rayan, Okafor (Balances squad mins security) |
| **`MAXIMUM_SQUAD`** | £100.0m / £0.0m | 60.89 | 69.13 | 75.64 | Haaland | **Verbruggen**, Timber, White, Calafiori, Frimpong, **James, Semenyo, Sarr, Haaland, Marmoush, Awoniyi** | **A.Becker**, Rayan, Ngumoha, Okafor (Selects Marmoush & Alisson) |

---

## 5. Background Progress System Architecture

- Module: [`backend/optimizer/progress_manager.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/optimizer/progress_manager.py) (`JobProgressManager`).
- Stages:
  1. `LOADING_FPL_DATA` (10%)
  2. `LOADING_MODEL_ARTIFACTS` (20%)
  3. `GENERATING_PROJECTIONS` (30%)
  4. `CALCULATING_PLAYER_XP` (40%)
  5. `BUILDING_MILP_PROBLEM` (50%)
  6. `SOLVING_SQUAD_OPTIMIZATION` (65%)
  7. `SELECTING_STARTING_XI` (80%)
  8. `SELECTING_CAPTAIN_VICE` (90%)
  9. `COMPUTING_DIAGNOSTICS` (95%)
  10. `FINALIZING_RESULTS` (100%)
- Endpoints:
  - `POST /api/v1/optimize/job` $\implies$ Starts background optimization task, returns `job_id`.
  - `GET /api/v1/optimize/status/{job_id}` $\implies$ Polls real-time stage progress.
  - `GET /api/v1/optimize/result/{job_id}` $\implies$ Fetches finished `OptimizationResponse`.
  - `POST /api/v1/optimize/compare_modes` $\implies$ Evaluates all 4 modes against the same frozen snapshot.

---

## 6. Position-Aware Price & Value Percentiles

For every player $p$ in position $\text{pos} \in \{\text{GKP}, \text{DEF}, \text{MID}, \text{FWD}\}$:
- **`pos_price_percentile`**: Percentile rank of price within position $\text{pos}$.
  - Raya (£6.0m GKP) $\to 95.0\%$ (Expensive GKP).
  - Gabriel (£6.0m DEF) $\to 92.0\%$ (Expensive DEF).
  - Igor Jesus (£6.0m FWD) $\to 35.0\%$ (Budget FWD).
- **`pos_xp_percentile`**: Percentile rank of xP within position $\text{pos}$.
- **`pos_value_percentile`**: Percentile rank of $\text{xP}/£\text{m}$ within position $\text{pos}$.

---

## 7. Verification & Test Suite

- Ran `python -m pytest`: **51 / 51 tests passed (100%)**.
- Created `tests/test_optimizer_modes_progress.py` testing job lifecycle, progress polling API, 4-mode comparison API, and positional percentiles.
- Pushed commit to `https://github.com/aadi1105/fpl-agent.git`.
