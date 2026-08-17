# Phase 1A — Fixture-Aware Gameweek Projections & UI Integration

---

## 1. Objective
Extend the baseline engine to support dynamic multi-gameweek projections (GW1 to GW8), home/away modifiers, 2026/27 DEFCON CBIT rules, multi-gameweek horizon optimization (`CURRENT_GW_PLUS_3`), and interactive dashboard UI.

---

## 2. Starting State
Static single-GW projections without fixture difficulty adjustments or 2026/27 DEFCON CBIT scoring rules.

---

## 3. Requirements
1. Map fixture schedules for all 20 teams across GW1–GW8.
2. Incorporate home/away factors (+5% home, -5% away) and fixture difficulty scaling (1 to 5).
3. Implement Poisson model for 2026/27 DEFCON CBIT rule ($P(\text{CBIT} \ge 10 \mid \lambda)$).
4. Support 4-GW weighted optimization (`CURRENT_GW_PLUS_3`: 55% / 20% / 15% / 10%).
5. Build interactive dashboard with position tabs and multi-GW fixture lookups.

---

## 4. Implementation Details

### Key Code Additions
* **Poisson DEFCON Calculation** ([`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py#L69-L82)):
  ```python
  def calculate_defcon_probability(self, cbit_match: float) -> float:
      if cbit_match <= 0.0: return 0.0
      prob_under_10 = sum((math.pow(cbit_match, k) * math.exp(-cbit_match)) / math.factorial(k) for k in range(10))
      return round(min(0.85, max(0.0, 1.0 - prob_under_10)), 3)
  ```
* **Weighted Multi-GW Horizon MILP Objective** ([`backend/optimizer/squad_optimizer.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/optimizer/squad_optimizer.py)):
  Maximized $\sum_{p} w_{\text{horizon}} \cdot xP_{p, gw}$.

---

## 5. Problems Discovered & Root Cause Analysis
* **UI Bug**: Dashboard displayed GW0 static $xP$ in every gameweek table column regardless of selected GW.
* **Root Cause**: Frontend JS hardcoded `gw0_xp` property across all table cells instead of indexing the selected `target_gw` breakdown.
* **Fix**: Updated [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html) to dynamically bind `bd[selected_gw].total_xp`.

---

## 6. Validation Results
* Created [`tests/test_phase1_fixtures.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase1_fixtures.py) and [`tests/test_phase1a_ui.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase1a_ui.py).
* Verified multi-GW projections generate fixture-specific variations.

---

## 7. Result
**COMPLETED SUCCESSFULLY**.

---

## 8. Development Prompt
Refer to [`docs/prompts/PHASE_1_BASELINE.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/prompts/PHASE_1_BASELINE.md).
