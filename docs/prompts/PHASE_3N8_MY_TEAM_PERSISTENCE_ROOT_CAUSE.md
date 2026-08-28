# PHASE 3N.8 — MY TEAM PERSISTENCE / RELOAD / DEFAULT-SQUAD ROOT-CAUSE AUDIT PROMPT

OBJECTIVE:
1. Audit and resolve root cause of Arsenal squad default, £1.5m bank, 2 FTs, and Wildcard chip appearing after reload.
2. Isolate test suite database execution using conftest.py so tests NEVER touch production fpl_engine.db.
3. Reset production fpl_engine.db user_squads table to empty unconfigured state (is_configured=False, picks=[]).
4. Verify unconfigured squad displays explicit setup prompt and never defaults to Arsenal or fake squads.
5. Maintain 100% test coverage (57/57 passing) across all 11 test suites without changing any ML/optimizer code.
