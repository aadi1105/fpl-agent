# Phase 1C — Team Strength & Fixture Context Layer

---

## 1. Objective
Replace neutral 1000.0 fallbacks with deterministic, data-driven team attacking and defensive strength ratings for all 20 Premier League teams. Integrate ratings into the projection engine using Bayesian shrinkage, home/away modifiers, and clamping bounds $[600.0, 1600.0]$.

---

## 2. Starting State
All team strength ratings were unpopulated ($0$), causing the engine to use neutral 1000.0 fallbacks for all opponents regardless of team quality.

---

## 3. Implementation Details

### Important Files
* [`backend/projections/team_ratings.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/team_ratings.py) — `TeamRatingCalculator` class.
* [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py) — Updated `ProjectionEngine` fixture integration.
* [`scripts/verify_phase1c.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/scripts/verify_phase1c.py) — Phase 1C validation script.
* [`tests/test_phase1c_ratings.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase1c_ratings.py) — Phase 1C unit test suite.

### Mathematical Formulation
1. **Per-Match Metrics**:
   $$\text{xG\_pg}_t = \frac{\sum_{p \in t} \text{xG}_p}{\text{games}_t}, \quad \text{xGA\_pg}_t = \frac{\sum_{p \in t} \text{xGA}_p / 11.0}{\text{games}_t}$$
2. **Observed Ratings Relative to League Average (1000.0 Baseline)**:
   $$\text{obs\_att}_t = 1000.0 \times \frac{\text{xG\_pg}_t}{\max(0.5, \text{avg\_league\_xg})}, \quad \text{obs\_def}_t = 1000.0 \times \frac{\max(0.5, \text{avg\_league\_xga})}{\max(0.3, \text{xGA\_pg}_t)}$$
3. **Bayesian Shrinkage toward 1000.0 Baseline**:
   $$w_t = \frac{\text{games}_t}{\text{games}_t + 5.0}, \quad \text{base\_att}_t = (w_t \cdot \text{obs\_att}_t) + ((1 - w_t) \cdot 1000.0)$$
4. **Home/Away & Clamping Bounds $[600.0, 1600.0]$**:
   $$\text{att\_h}_t = \text{clamp}(\text{base\_att}_t \times 1.05, 600.0, 1600.0), \quad \text{att\_a}_t = \text{clamp}(\text{base\_att}_t \times 0.95, 600.0, 1600.0)$$

---

## 4. Problems Discovered & Resolved
* **Bug Encountered**: `AttributeError: 'NoneType' object has no attribute 'team_a_difficulty'` when `fixture` was `None`.
* **Root Cause**: Operator precedence in `fixture.team_a_difficulty if is_home else fixture.team_h_difficulty if fixture else 3` evaluated `fixture.team_a_difficulty` when `is_home=True` before checking `if fixture`.
* **Fix**: Isolated parenthesized expression in [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py#L247):
  ```python
  diff = (fixture.team_a_difficulty if is_home else fixture.team_h_difficulty) if fixture else 3
  ```

---

## 5. Validated Team Strength Summary

| Team | Att H | Att A | Def H | Def A | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Man City (MCI)** | `1389.1` | `1256.8` | `1151.7` | `1042.0` | Elite Attack |
| **Arsenal (ARS)** | `1257.3` | `1137.6` | **`1600.0`** | `1554.3` | Home Def pre-clip $1717.87 \to$ Clamped at **1600.0** |
| **Bournemouth (BOU)** | `1233.5` | `1116.1` | `972.0` | `879.5` | Average Attack / Weak Defence |
| **Sunderland (SUN)** | `782.9` | `708.4` | `1016.9` | `920.1` | Newly Promoted — Regressed toward 1000.0 |

---

## 6. Fixture Difficulty Scenarios

### Attacker Scenarios (Haaland)
* **Strong Att vs Weak Def** (`vs BOU (H)`): Opp Def `879.5` | Att Modifier `1.194` | xG `0.773` | **Total xP: 5.49**
* **Strong Att vs Elite Def** (`vs ARS (A)`): Opp Def `1600.0` | Att Modifier `0.600` | xG `0.389` | **Total xP: 3.83**

### Defender Scenarios (Gabriel)
* **Elite Def vs Weak Att** (`vs SUN (H)`): Opp Att `708.4` | CS Ratio `2.372` | CS Prob `0.750` | **Total xP: 5.24**
* **Elite Def vs Strong Att** (`vs MCI (A)`): Opp Att `1389.1` | CS Ratio `1.063` | CS Prob `0.340` | **Total xP: 4.60**

---

## 7. Result
**COMPLETED SUCCESSFULLY**. Verified via `scripts/verify_phase1c.py` and 20/20 test suite.

---

## 8. Development Prompt
Refer to [`docs/prompts/PHASE_1C_TEAM_STRENGTH.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/prompts/PHASE_1C_TEAM_STRENGTH.md).
