# PHASE 3N.12 AUDIT REPORT

## A. Expected Minutes

### Current implementation:
- **Pipeline**: `player availability/status` $\to$ `MinutesPredictor` (LightGBM `expected_minutes_v2.pkl` & `minutes_start_v1.pkl`) $\to$ `ProjectionEngine.calculate_player_xp_breakdown` $\to$ `PlayerProjection` $\to$ `SquadOptimizer`.
- **Baseline**: `MinutesPredictor` evaluates each player independently based on historical starts, recent minutes, price tier, and fixture difficulty.

### Competition issue:
- Independent models can predict high expected minutes for multiple players on the same club who compete for mutually exclusive starting roles (e.g. Goalkeepers).

### Affected groups:
- **Manchester City GKPs**: Donnarumma (90 mins), Bettinelli (85 mins baseline), Rulli (85 mins baseline).
- **Manchester United GKPs**: Lammens (90 mins), Darlow (85 mins baseline), Bayındır (85 mins baseline).

### Minimal fix:
- Integrated club-level role competition reconciliation in [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py):  
  For mutually exclusive positions (GKP), the starting GKP with recent playing evidence is assigned primary expected minutes (85–90 xMins), while reserve/backup team-mate GKPs are reconciled to 0.0 xMins. Outfield player LightGBM predictions are preserved to support tactical multi-position role flexibilities.

### Before/after examples:

1. **Manchester City GKPs (MCI GKP)**:
   - Donnarumma: Baseline 83.6 xMins $\to$ **Reconciled 90.0 xMins**
   - Bettinelli: Baseline 85.0 xMins $\to$ **Reconciled 0.0 xMins**
   - Rulli: Baseline 85.0 xMins $\to$ **Reconciled 0.0 xMins**
   - *Total Team GKP Minutes*: 253.6 mins $\to$ **90.0 mins** (Matches physical matchday capacity)

2. **Manchester United GKPs (MUN GKP)**:
   - Lammens: Baseline 82.4 xMins $\to$ **Reconciled 90.0 xMins**
   - Darlow: Baseline 85.0 xMins $\to$ **Reconciled 0.0 xMins**
   - Bayındır: Baseline 85.0 xMins $\to$ **Reconciled 0.0 xMins**
   - *Total Team GKP Minutes*: 277.4 mins $\to$ **90.0 mins** (Matches physical matchday capacity)

3. **Arsenal Defenders (ARS DEF)**:
   - Gabriel: 68.4 xMins (Preserved)
   - Calafiori: 59.5 xMins (Preserved)
   - White: 60.1 xMins (Preserved)
   - Timber: 55.0 xMins (Preserved)

4. **Liverpool Midfielders (LIV MID)**:
   - Gakpo: 68.1 xMins (Preserved)
   - Szoboszlai: 68.1 xMins (Preserved)
   - Wirtz: 64.3 xMins (Preserved)

5. **Chelsea Forwards (CHE FWD)**:
   - João Pedro: 68.2 xMins (Preserved)
   - N.Jackson: 55.0 xMins (Preserved)

### Optimizer impact:
- The optimizer consumes reconciled expected minutes, ensuring backup GKPs with zero starting minutes are never evaluated for starting XI slots.

---

## B. Data Freshness

- **Displayed last sync**: `2026-08-20` (in UI header banner `#data-synced-banner`)
- **Actual last successful sync**: `2026-08-26T19:58:43.811308` (backend database snapshot timestamp)
- **Current GW**: GW1
- **Next GW**: GW2
- **Player data timestamp**: `2026-08-26`
- **Fixture data timestamp**: `2026-08-26`
- **Availability timestamp**: `2026-08-26`
- **Projection timestamp**: `2026-08-26`

### Root cause of discrepancy:
- `frontend/index.html` line 246 contained a hardcoded HTML text string `FPL Data Last Synced: 2026-08-20 (Canonical 2026/27 Official API)`. `fetchStateStatus()` updated `#current-state-banner` but did not update `#data-synced-banner`.

### Fix:
- Updated `fetchStateStatus()` in [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html) to dynamically set `#data-synced-banner` text from backend `data.generated_at` timestamp.

---

## C. Tests

- **Existing**: 73 / 73
- **New**: 3 / 3 in [`tests/test_phase3n12_minutes_and_freshness.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n12_minutes_and_freshness.py)
- **Total**: **76 / 76 passing**

---

## D. Final Verdict

**`EXPECTED MINUTES + DATA FRESHNESS VERIFIED`**
