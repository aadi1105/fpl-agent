# PHASE 3N.18 — MY TEAM SUBSTITUTION FLOW + STATE RELIABILITY FIX PROMPT

OBJECTIVE:
1. Identify and fix root cause of second-interaction dead clicks after substitutions.
2. Redesign substitution UX into a clean FPL-style flow (`[ ↔️ SUBSTITUTE ]` -> Clean Target Cards Grid with `[ ← BACK ]` and `[ CANCEL ]`).
3. Enforce real-time FPL formation validation with `🔒 LOCKED` status cards and clear explanations (e.g., "fewer than 3 Defenders").
4. Implement automatic Captain/Vice-Captain status transfers when a Captain/Vice-Captain is benched to keep captaincy in the starting XI.
5. Create regression test suite (`tests/test_phase3n18_substitution_ux_and_state.py`) verifying consecutive substitutions, formation checks, captain transfers, and browser state reset (98/98 total tests passing across 22 test suites).
