# PHASE 3N.16 — MY TEAM COMMAND CENTER: SQUAD MANAGEMENT ENTRY POINT PROMPT

OBJECTIVE:
1. Add prominent `[ ✏️ EDIT SQUAD ]` and `[ ⚡ COMPARE VS OPTIMAL XI ]` action buttons to the My Team Command Center header.
2. Integrate functional `#my-team-modal` squad editor allowing users to add/remove players, set bank value, free transfers, and active chip with full FPL composition validation.
3. Support direct FPL-style formation pitch rendering, player insight modals, captain/vice-captain assignments, and starter <-> bench player substitutions.
4. Enforce persistent single source of truth via `/api/v1/user-squad` surviving page refreshes, tab switches, optimizer runs, and browser navigation (never defaulting to Arsenal squad).
5. Add test suite `tests/test_phase3n16_my_team_command_center.py` (92/92 total tests passing) without modifying any underlying ML/optimizer models.
