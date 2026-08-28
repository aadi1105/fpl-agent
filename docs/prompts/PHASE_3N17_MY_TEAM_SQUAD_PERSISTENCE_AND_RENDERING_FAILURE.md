# PHASE 3N.17 — MY TEAM SQUAD PERSISTENCE + RENDERING FAILURE PROMPT

OBJECTIVE:
1. Root cause and eliminate the "0 Players / 0-0-0 pitch" rendering failure on My Team Command Center.
2. Fix backend API payload mapping in `get_user_squad_dict` to explicitly include `starting_11`, `bench`, `captain`, and `vice_captain` root keys.
3. Fix frontend hydration in `renderUserSquadPage(squadData)` to extract starting XI and bench players robustly from `starting_11`/`bench` or `picks`.
4. Ensure persistent single source of truth via `/api/v1/user-squad` surviving page refresh, tab switches, and hard reloads without fallback to default or Arsenal squad.
5. Create regression test suite (`tests/test_phase3n17_squad_persistence_and_hydration.py`) verifying API payload root keys and real save -> refresh -> re-hydrate lifecycle (95/95 total tests passing across all 21 test suites).
