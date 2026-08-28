# PHASE 3M — DYNAMIC GAMEWEEK STATE & CURRENT PLAYER DATA REFRESH

OBJECTIVE:
Build a reliable, refreshable CURRENT GAMEWEEK STATE layer so that every future gameweek optimization is based on what is true RIGHT NOW — while keeping historical data clean and leak-free.

Core Features:
1. Canonical Current Gameweek State layer (immutability of historical data, mutability of current state).
2. Synchronization with official FPL API for status, availability (`chance_of_playing`), injuries, suspensions, current prices, current clubs.
3. Player Eligibility engine (excluding `chance_of_playing == 0` or long-term unavailable players from optimizer).
4. Haaland, Pope, Ekitiké, Awoniyi, Nelson transfer and eligibility audit.
5. Idempotent state refresh process with data quality tracking and snapshot versioning (`2026_27_GW1_STATE_v1`).
6. Automated regression test suite in `tests/test_phase3m_current_state.py`.
7. DO NOT RUN GW2 OPTIMIZER OR GENERATE GW2 RECOMMENDED SQUAD.
