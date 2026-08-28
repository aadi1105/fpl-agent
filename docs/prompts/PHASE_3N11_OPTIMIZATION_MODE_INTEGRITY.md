# PHASE 3N.11 — OPTIMIZATION MODE INTEGRITY + DECISION ENGINE AUDIT PROMPT

OBJECTIVE:
1. Audit and verify the mathematical objective function, horizon weighting, and constraints for NEXT GW, MEDIUM TERM, and LONG TERM optimization modes.
2. Build a deterministic synthetic test proving that the 3 modes solve genuinely different mathematical objectives.
3. Perform real production runs across all 3 modes using current player data and record XI, bench, formation, captain, and decision traces.
4. Audit expected-minutes competition, captain objective, formation optimization, and squad-level MILP solver construction.
5. Maintain 100% test coverage (73/73 passing) across 15 test suites without changing any underlying ML/optimizer models.
