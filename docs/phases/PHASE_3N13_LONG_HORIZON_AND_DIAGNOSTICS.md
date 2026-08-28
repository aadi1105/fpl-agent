# PHASE 3N.13 REPORT

## 1. Long-Term Horizon
- **Configured horizon**: GW2, GW3, GW4, GW5, GW6, GW7, GW8 (7 Gameweeks)
- **Actual backend horizon**: GW2 to GW8 (`horizon_gws = [2, 3, 4, 5, 6, 7, 8]`)
- **Weighting**: `[0.30, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05]`
- **Status**: **VERIFIED & DYNAMICALLY ALIGNED**

---

## 2. Diagnostics
- **Root cause**:  
  1. Frontend `#metric-horizon-title` and `#diagnostics-panel-title` had hardcoded text strings `"4-GW WEIGHTED HORIZON"` and `"4-GW Outlook & Diagnostics"`.  
  2. Backend `GET /api/v1/projections/diagnostics` had hardcoded 4-GW loop bounds starting at `target_gw` rather than accepting `mode` parameter and starting at future optimization horizon `target_gw + 1` (GW2).  
- **Fix**:  
  1. Added `mode` query parameter to `get_diagnostics` in [`backend/main.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/main.py) to dynamically return mode-specific horizon projections starting at GW2.  
  2. Updated `fetchDiagnostics(mode)` and `renderDiagnosticsTable(data, mode)` in [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html) to dynamically update metric titles, panel titles, and table headers.  
- **API status**: HTTP 200 OK (<0.2s cached response)
- **Rendered successfully**: YES (Renders mode-aware horizon breakdown without getting stuck on "Loading...")
- **Status**: **VERIFIED**

---

## 3. Darlow
- **Expected minutes**: 0.0 xMins (Reconciled)
- **Starting probability**: 0.00
- **Competition group**: Manchester United GKPs (Lammens 90.0 xMins primary starter vs Darlow / Bayındır 0.0 xMins reserves)
- **Status**: **RESOLVED**
- **Reason selected**: Static DB table `PlayerProjection` contained pre-reconciliation projections from an earlier run. Regenerated DB projections via `engine.run_projections(start_gw=1, end_gw=8, force=True)`, setting Darlow DB projections to 0.0 xP. Darlow is no longer selected. Rushworth (£4.5m, 3.48 xP) is selected as starting GKP.

---

## 4. Mode Verification

### Next GW:
- **Horizon**: GW2 Only (`[1.0]`)
- **Formation**: 3-5-2
- **XI**: Rushworth, Guéhi, White, Gvardiol, **B.Fernandes (C - £12.0m)**, Saka, Mbeumo, Szoboszlai, Dewsbury-Hall, Isak, McBurnie.
- **Score**: **50.00 GW1 xP** (56.15 Horizon Score)

### Medium:
- **Horizon**: GW2–GW5 (`[0.55, 0.20, 0.15, 0.10]`)
- **Formation**: 3-5-2
- **XI**: Rushworth, Guéhi, White, Gvardiol, Saka, **Palmer (£9.5m)**, Mbeumo, Szoboszlai, Gakpo, **Isak (C)**, **João Pedro (£7.5m)**.
- **Score**: 49.43 GW1 xP (**54.99 4-GW Horizon Score**)

### Long:
- **Horizon**: GW2–GW8 (`[0.30, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05]`)
- **Formation**: **3-4-3**
- **XI**: Rushworth, Guéhi, White, Gvardiol, Palmer, Mbeumo, Szoboszlai, Gakpo, **Isak (C)**, **Thiago (£8.0m 3rd FWD)**, João Pedro.
- **Score**: 48.62 GW1 xP (**54.69 7-GW Horizon Score**)

---

## 5. Tests

- **Targeted tests**: 4 / 4 in [`tests/test_phase3n13_long_horizon_and_diagnostics.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n13_long_horizon_and_diagnostics.py)
- **Full suite**: **80 / 80 passing** across 17 test suites

---

## 6. Final Verdict

**`LONG HORIZON + DIAGNOSTICS VERIFIED`**
