# DATA PIPELINE — 2026/27 CURRENT-STATE, TRANSFERS & REALITY AUDIT

**Last Updated**: 2026-08-27  
**Data Sync Timestamp**: **`2026-08-20T23:18:29Z`**  
**Current State Snapshot**: **`2026_27_GW1_STATE_v1`**  
**Canonical Data Source**: **Official FPL API (`/bootstrap-static/` & `/fixtures/`)**  

---

## 1. Overview & Data Ingestion Architecture

The FPL Decision Engine ingests current-season player, team, availability, price, and fixture data directly from the official Fantasy Premier League API endpoints:

- **Bootstrap Endpoint**: `https://fantasy.premierleague.com/api/bootstrap-static/`
- **Fixtures Endpoint**: `https://fantasy.premierleague.com/api/fixtures/`

Ingestion and database synchronization are handled by [`backend/ingestion/fpl_api.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ingestion/fpl_api.py) and schema models defined in [`backend/models.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/models.py).

---

## 2. Test Database Isolation Architecture

1. **Production Database (`fpl_engine.db`)**:
   - Holds canonical player, team, fixture, projection, and persistent user squad state (`UserSquad`).
2. **Isolated Test Database (`fpl_engine_test.db`)**:
   - `conftest.py` automatically overrides `DATABASE_URL` for pytest runs.
   - All tests execute exclusively against `fpl_engine_test.db`, guaranteeing zero mutation of production `fpl_engine.db`.

---

## 3. Test Suite Coverage (73 / 73 Passing)

- [`tests/test_phase3n11_mode_integrity.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n11_mode_integrity.py): 3/3 passing synthetic differentiation, real production mode differentiation, and squad rules tests.
- [`tests/test_phase3n10c_optimizer_isolation.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n10c_optimizer_isolation.py): 4/4 passing cached diagnostics, optimizer job result payload, state isolation, and frontend hydration tests.
- [`tests/test_phase3n10_substitution_and_modal.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n10_substitution_and_modal.py): 4/4 passing modal close controls, direct starter/bench substitution, captain transfer, and persistence tests.
- [`tests/test_phase3n9_my_team_v2_fpl_experience.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n9_my_team_v2_fpl_experience.py): 5/5 passing V2 schema, starter/captain persistence, triple captain multiplier, invalid size rejection, and unconfigured state tests.
- [`tests/test_phase3n8_persistence_root_cause.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n8_persistence_root_cause.py): 7/7 passing DB safety guard, empty unconfigured state, no Arsenal fallback, exact 15 player save/reload, bank/FT/chip coherence, and no-overwrite tests.
- [`tests/test_phase3n7_financial_state_and_legal_transfers.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n7_financial_state_and_legal_transfers.py): 3/3 passing bank zero persistence, unaffordable transfer rejection, and actionable vs theoretical separation tests.
- [`tests/test_phase3n6_loading_and_concurrency.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n6_loading_and_concurrency.py): 5/5 passing fast canonical player API, search matching, SQLite WAL mode, single job creation, and failed job lifecycle tests.
- [`tests/test_phase3n5_calibration_and_persistence.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n5_calibration_and_persistence.py): 4/4 passing calibration v2 active, unconfigured squad zero-picks, squad save/reload persistence, and squad replacement tests.
- [`tests/test_phase3n4_gameweek_and_visuals.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n4_gameweek_and_visuals.py): 5/5 passing gameweek index consistency, no-GW0 label, Bruno projection decomposition, optimal XI decision trace, and shirt SVG tests.
- [`tests/test_phase3n3_mode_integrity.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n3_mode_integrity.py): 6/6 passing synthetic mode differentiation, mode mapping, compare modes API, actionable 1-FT transfer search, price consistency, and SVG shirt asset tests.
- [`tests/test_phase3n2b_live_verification.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n2b_live_verification.py): 4/4 passing modal CSS, save isolation, projection reuse performance, and single job creation tests.
- [`tests/test_phase3n2a_my_team_ux.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n2a_my_team_ux.py): 5/5 passing My Team CRUD, validation, persistence, comparison, and UI element tests.
- [`tests/test_frontend_regression.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_frontend_regression.py): 2/2 passing HTML structure and script tag boundary tests.
- [`tests/test_phase3n2_reality_audit.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n2_reality_audit.py): 9/9 passing reality audit tests.
- [`tests/test_phase3n1_reality_audit.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n1_reality_audit.py): 7/7 passing reality audit tests.
