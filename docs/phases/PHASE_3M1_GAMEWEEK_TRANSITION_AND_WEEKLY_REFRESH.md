# PHASE 3M.1 — GAMEWEEK TRANSITION, WEEKLY REFRESH & OPTIMIZER UX FOUNDATION REPORT

**Date**: 2026-08-26  
**Status**: `COMPLETED & EMPIRICALLY VERIFIED`  
**Gameweek Transition Verified**: `GW1 -> GW2 Transition Demonstrated & Validated`  
**Active Gameweek Snapshot**: `2026_27_GW2_STATE_v1`  
**Frozen GW1 Snapshot**: `2026_27_GW1_STATE_v1 (Immutable)`  
**Data Quality Status**: `100% CLEAN (0 missing prices, 0 missing teams, 0 missing positions, 0 duplicates)`  
**Regression Test Suite**: `6 / 6 tests passing (tests/test_phase3m1_transition.py)`  
**Final Safety Gate Verdict**: **`SAFE TO PROCEED TO GW2 DECISION OPTIMIZATION`**  

---

## 1. Gameweek Transition (GW1 -> GW2) & Snapshot Lifecycle

Phase 3M.1 fixes and verifies temporal gameweek transitions:

1. **Gameweek Advancement (`CurrentGameStateManager.advance_gameweek()`)**:
   - Updates `Gameweek.is_current` flags in database (GW1 `is_current=False`, `is_previous=True`, `finished=True`; GW2 `is_current=True`).
   - Generates and active state snapshot `2026_27_GW2_STATE_v1`.
2. **Historical Immutability**:
   - Frozen GW1 snapshot `2026_27_GW1_STATE_v1` remains byte-for-byte and logically intact.
   - Past match observations, realized FPL points, and original GW1 projections are preserved without over-writing.
3. **Idempotent Refresh Pipeline (`refresh_current_gameweek()`)**:
   - Synchronizes current prices, player availability (`chance_of_playing_next_round`), transfers, and role status.
   - Runs `ProjectionEngine.run_projections(start_gw=2, end_gw=9, source="internal")` updating 4,792 projection records across the 8-GW horizon.

---

## 2. Multi-Horizon Optimization Modes & Jaccard Differentiation

Phase 3M.1 implements 4 distinct optimization horizons in [`backend/optimizer/squad_optimizer.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/optimizer/squad_optimizer.py):

| Mode Name | Display Label | Horizon GWs | Weight Vector ($w$) | Squad Cost | Starting XI xP | Captain |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: |
| **`NEXT_GW`** | Next Gameweek Only | GW2 | `[1.0]` | £100.0m | 50.27 pts | Bruno Fernandes |
| **`SHORT_TERM`** | Short Term Horizon | GW2–GW3 | `[0.65, 0.35]` | £100.0m | 50.34 pts | Bruno Fernandes |
| **`MEDIUM_TERM`**| Medium Term Horizon | GW2–GW5 | `[0.55, 0.20, 0.15, 0.10]` | £100.0m | 50.30 pts | Bruno Fernandes |
| **`LONG_TERM`** | Long Term (High Uncertainty)| GW2–GW8 | `[0.30, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05]` | £100.0m | 50.34 pts | Bruno Fernandes |

### **Compositional Jaccard Similarity Matrix Across Modes**:

$$\begin{pmatrix}
 & \text{NEXT\_GW} & \text{SHORT\_TERM} & \text{MEDIUM\_TERM} & \text{LONG\_TERM} \\
\text{NEXT\_GW} & 1.00 & 0.58 & 0.58 & 0.58 \\
\text{SHORT\_TERM} & 0.58 & 1.00 & 0.67 & 0.88 \\
\text{MEDIUM\_TERM} & 0.58 & 0.67 & 1.00 & 0.76 \\
\text{LONG\_TERM} & 0.58 & 0.88 & 0.76 & 1.00
\end{pmatrix}$$

**Outcome**: Modes are mathematically and compositionally distinct (e.g. 42% squad difference between `NEXT_GW` and `MEDIUM_TERM`).

---

## 3. "My Team" Persistent View & Comparison Architecture

- **User Squad Manager**: Implemented [`backend/user/user_squad.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/user/user_squad.py).
- **Persistent User State**: Stored in SQLite (`UserSquad` & `UserPick` models).
- **Comparative Analysis**:
  - Automatically compares user squad vs optimal squad.
  - Tagging: `KEEP`, `TRANSFER IN`, `TRANSFER OUT`, `BENCH CHANGE`.
  - Calculates point differential and transfer differentials (e.g. SELL Player A $\to$ BUY Player B, expected points gain).

---

## 4. Final Safety Gate Evaluation

- 1. System automatically detects GW2: `PASS`
- 2. GW1 state remains immutable: `PASS`
- 3. GW1 results become historical data: `PASS`
- 4. GW2 state snapshot exists (`2026_27_GW2_STATE_v1`): `PASS`
- 5. GW2 fixtures are active: `PASS`
- 6. Current clubs are correct: `PASS`
- 7. Current prices are correct: `PASS`
- 8. Availability is current: `PASS`
- 9. Long-term unavailable players cannot be selected: `PASS`
- 10. Haaland remains correctly represented: `PASS`
- 11. v2 projection is used: `PASS`
- 12. Optimizer receives GW2 state: `PASS`
- 13. My Team is persistently represented: `PASS`
- 14. My Team and Optimal Team can be compared: `PASS`
- 15. Optimization modes genuinely represent different horizons: `PASS`
- 16. Refresh is idempotent: `PASS`
- 17. Frontend clearly identifies current GW and data freshness: `PASS`
- 18. All critical tests pass: `PASS` (6/6 passing in `tests/test_phase3m1_transition.py`)

### **`FINAL VERDICT: SAFE TO PROCEED TO GW2 DECISION OPTIMIZATION`**

---

## 5. Stop Condition Confirmation

* **Phase 3M.1 Gameweek Transition & Refresh System**: `COMPLETED`
* **GW2 Recommended Squad Produced**: `NO`
* **Transfers / Chips Executed**: `NO (Awaiting explicit user direction for Phase 3N)`
