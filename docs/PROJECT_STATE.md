# PROJECT STATE — SINGLE SOURCE OF TRUTH

**Last Updated**: 2026-08-30  
**Phase**: Phase 3N.22 — Fix Gameweek History Using Correct FPL Manager + Current Gameweek  
**Current Directive**: **`VERDICT: ACCEPTANCE PASSED. FIXED MANAGER ENTRY ID RESOLUTION IN FPLHISTORYSERVICE (BACKEND/SERVICES/FPL_HISTORY_SERVICE.PY). ELIMINATED FALLBACK TO ENTRY ID 1 (STRANGER SQUAD). FOR UNLINKED ACCOUNTS, GAMEWEEK SNAPSHOT CONSUMES THE USER'S OWN SAVED SQUAD (HAALAND, B.FERNANDES, MBEUMO, RAYA, CALAFIORI, SZOBOSZLAI...). FOR LINKED ACCOUNTS, VALIDATED REQUESTED_ENTRY_ID == CONFIGURED_ENTRY_ID (RETURNING EXPLICIT MANAGER_MISMATCH ERROR ON UNLINKED IDS). FIXED GAMEWEEK STATUS LABELING: GW1 IS COMPLETED, GW2 IS LIVE, GW3+ IS UPCOMING. ISOLATED CACHE KEYS BY ENTRY_ID AND GAMEWEEK (ENTRY_PICKS_{ENTRY_ID}_GW_{GW}). CREATED TEST SUITE (TESTS/TEST_PHASE3N22_MANAGER_ID_AND_GAMEWEEK_FIX.PY). ALL 120 TESTS PASSING CLEANLY ACROSS ALL 26 TEST SUITES.`**  

---

## A. PROJECT OBJECTIVE

Build a trustworthy Fantasy Premier League (FPL) decision-support system that:
1. Predicts gameweek-specific expected FPL points ($xP$) using statistical and machine learning models trained exclusively on pre-deadline data (no forward-looking leakage).
2. Optimizes squad selection, transfer plans, captaincy, and bench structure using those verified point projections.

---

## B. CURRENT PRODUCTION MODELS & RUNTIME ARTIFACTS

The active production pipeline evaluates player projections via `backend/projections/engine.py` consuming the following runtime models:

| Component | Class Name | Deployed Model File | Path | SHA256 Hash |
| :--- | :--- | :--- | :--- | :--- |
| **Expected Minutes** | `MinutesPredictor` | `expected_minutes_v2.pkl` | `models/expected_minutes_v2.pkl` | `73ca103093d46d9571ff26a635ac2ebfe4e760bf6463fbbeed8653630f9a2e6f` |
| **Start Probability** | `MinutesPredictor` | `minutes_start_v1.pkl` | `models/minutes_start_v1.pkl` | `098a7da9db81a986d34b6b6ecfb0cf2382f6cfcf51adcefbab0f5d5351a0ee33` |
| **Minutes Regression**| `MinutesPredictor` | `minutes_regression_v1.pkl` | `models/minutes_regression_v1.pkl` | `67d6627b19564ccf2c1ff65dcae98715c0e181c010bb116b49040003b0704439` |
| **Expected Goals (xG)**| `XGPredictor` | `xg_v2.pkl` | `models/xg_v2.pkl` | `1dc98d1f671a25b39414e548ac123ddffc6df14545ee0ed96f5b7aa2dd62b9a7` |
| **Expected Assists (xA)**| `XAPredictor` | `xa_v2.pkl` | `models/xa_v2.pkl` | `edde5f8dee0b01f0165cdd2e12e3dc164a2cebfa780d603a1ee6833c8ca94819` |
| **Clean Sheet (CS)** | `CSPredictor` | `cs_v1_lgbm.pkl` | `backend/ml/models/cs_v1_lgbm.pkl` | `2e16a5bed1b2cdf32a82916b3f71c4c1a798f8287951e70ceca8d08ca6bc4be8` |
| **DEFCON** | `DEFCONPredictor` | Built-in Poisson Process | `backend/ml/defcon_predictor.py` | `N/A (Analytical Poisson Model)` |
| **CS Calibrator** | `IsotonicRegression` | `cs_calibration_v1.pkl` | `backend/ml/models/cs_calibration_v1.pkl` | `f8237b16f806065b263bbf4df9eb5fcae135bc078b54e3d360faad2515b630b1` |
| **xP Calibrator Layer v2**| `ProjectionEngine` | `expected_xp_calibrated_v2.json`| `backend/ml/models/expected_xp_calibrated_v2.json` | `Model D Piecewise + Role Active` |
| **Current State Engine**| `CurrentGameStateManager`| `2026_27_GW1_STATE_v1` | `backend/ingestion/current_state.py` | `Active State Snapshot Layer` |
| **FPL History Service**| `FPLHistoryService` | Gameweek History & Live API | `backend/services/fpl_history_service.py` | `Historical Picks & Live Scoring Service` |
| **User Squad Manager** | `UserSquadManager` | Persistent My Team V2 | `backend/user/user_squad.py` | `Persistent User Squad View V2` |

---

## C. VALIDATED COMPONENTS & EMPIRICAL RESULTS

1. **Phase 3N.22 Manager Entry ID & Gameweek Detection Fix**:
   - Eliminated fallback to Entry ID `1` (stranger squad).
   - Bound Gameweek snapshots to the user's actual saved squad (`Haaland, B.Fernandes, Mbeumo, Raya, Calafiori, Szoboszlai...`).
   - Fixed Gameweek status labeling (`GW1 COMPLETED`, `GW2 🔴 LIVE`, `GW3 UPCOMING`).
   - Isolated cache keys by manager `entry_id` & `gameweek`.
   - Test suite passing: **120 / 120 tests passing**.
   - Safety verdict: **`ACCEPTANCE PASSED`**.

---

## D. CURRENT STOP CONDITION

**WE HAVE COMPLETED PHASE 3N.22 FIX GAMEWEEK HISTORY USING CORRECT FPL MANAGER + CURRENT GAMEWEEK.**  
**SAFETY VERDICT: ACCEPTANCE PASSED.**  
**AWAITING USER DIRECTION FOR NEXT PHASE.**
