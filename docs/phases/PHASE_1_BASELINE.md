# Phase 1 — Baseline Projection Engine & Squad Optimizer

---

## 1. Objective
Establish the initial deterministic statistical baseline projection engine and Google OR-Tools squad optimizer to solve the first demonstrable project milestone:
> **"Give the system £100m and a gameweek; it returns the mathematically optimal legal squad according to our current projection model."**

---

## 2. Starting State
New codebase initialization. No database schemas, data ingestion pipelines, projection engines, or optimization algorithms existed.

---

## 3. Requirements
1. Build Python FastAPI backend with SQLite database.
2. Ingest official FPL API player, team, and fixture data.
3. Formulate price-tier baseline for underlying player per-90 metrics.
4. Build OR-Tools MILP squad optimizer enforcing FPL constraints (£100.0m budget, 15 players, position bounds, max 3 players per club).
5. Build minimal web dashboard interface.

---

## 4. Implementation Details

### Important Files
* [`backend/database.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/database.py) — SQLite engine and session factory.
* [`backend/models.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/models.py) — SQLAlchemy ORM schemas (`Team`, `Player`, `Gameweek`, `Fixture`).
* [`backend/ingestion/fpl_api.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ingestion/fpl_api.py) — FPL API data collector.
* [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py) — Deterministic baseline projection engine.
* [`backend/optimizer/squad_optimizer.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/optimizer/squad_optimizer.py) — Google OR-Tools MILP squad solver.

### Baseline Price-Tier Metrics Table
```python
PRICE_TIER_DEFAULTS = {
    ElementType.DEF.value: {
        "high": {"xg90": 0.08, "xa90": 0.15, "bps90": 20.0, "cbit90": 6.5},  # > £6.0m
        "mid":  {"xg90": 0.05, "xa90": 0.08, "bps90": 16.0, "cbit90": 7.0},  # £5.0m - £5.5m
        "low":  {"xg90": 0.02, "xa90": 0.03, "bps90": 12.0, "cbit90": 6.0}   # < £5.0m
    },
    ...
}
```

---

## 5. Problems Discovered & Root Cause Analysis
* **Issue**: Initial cheap defenders had zero underlying xG in raw FPL API data.
* **Root Cause**: Players with $< 180$ minutes lacked sufficient historical sample size.
* **Fix**: Implemented price-tier fallbacks (`high`, `mid`, `low`) when total minutes $< 180$.

---

## 6. Validation Results
* Created unit tests in [`tests/test_ingestion.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_ingestion.py) and [`tests/test_optimizer.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_optimizer.py).
* Confirmed optimizer selects legal 15-player squad within £100.0m.

---

## 7. Current Limitations
* Projections in Phase 1 were static and did not vary by opponent or fixture location.

---

## 8. Result
**COMPLETED SUCCESSFULLY**.

---

## 9. Development Prompt
Refer to [`docs/prompts/PHASE_1_BASELINE.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/prompts/PHASE_1_BASELINE.md).
