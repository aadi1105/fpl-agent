# PHASE 3N.10 — MY TEAM PLAYER INTERACTION + SUBSTITUTION FLOW PROMPT

OBJECTIVE:
1. Fix Player Insight modal close button (`#modal-close`), backdrop click, and Escape key listeners.
2. Implement FPL-style direct player substitution flow between starters and bench players.
3. Enforce legal FPL formation constraints (1 GKP, 3-5 DEF, 2-5 MID, 1-3 FWD) during substitutions.
4. Handle captain/vice-captain state safely when a captain is moved to the bench.
5. Persist starting XI and bench order to backend SQLite database without consuming FTs or changing bank balance.
6. Maintain 100% test coverage (66/66 passing) across 13 test suites without changing any underlying ML/optimizer models.
