# Phase 1B — Projection Arithmetic Audit

---

## 1. Objective
Conduct a full mathematical audit of all projection component calculations (xG, xA, CS, DEFCON, Bonus, Saves, Cards) across top players to verify zero zero-division errors, zero ungrounded multipliers, and clean numeric behavior.

---

## 2. Starting State
Unverified multiplier pipeline. Suspected artificial scaling on specific players.

---

## 3. Major Bug Discovered & Root Cause Analysis

### The 500-Rating Fallback Bug
* **Symptom**: Certain players against opponents with unpopulated team defensive ratings received an artificial **`2.10x` attacking multiplier**, inflating expected points to ungrounded levels.
* **Root Cause**: When `opponent_team.strength_defence_home` was `0` or `None`, fallback logic defaulted to `500.0` instead of `1000.0`.
  $$\text{raw\_att\_mult} = \frac{1000.0}{500.0} \times 1.05 = 2.10$$
* **Fix**: Updated `ProjectionEngine` to default missing team ratings strictly to **`1000.0`** (league average):
  $$\text{raw\_att\_mult} = \frac{1000.0}{1000.0} \times 1.05 = 1.05$$

---

## 4. Audited Player Examples

| Player | Position | Cost | GW1 Fixture | Opp Def Rating | Att Modifier | xG Match | Total GW1 xP |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Erling Haaland** | FWD | £15.5m | vs BOU (H) | `1000.0` (Fallback) | `1.050` | `0.680` | **5.49 xP** |
| **Cole Palmer** | MID | £9.5m | vs FUL (A) | `1000.0` (Fallback) | `0.950` | `0.370` | **4.25 xP** |
| **Gabriel Magalhães** | DEF | £8.0m | vs COV (H) | `1000.0` (Fallback) | `1.050` | `0.089` | **4.84 xP** |
| **Taji O'Riley** | MID | £5.5m | vs CRY (H) | `1000.0` (Fallback) | `1.050` | `0.262` | **5.12 xP** |

---

## 5. Critical Distinction: Arithmetic Correctness vs. Predictive Accuracy

> [!IMPORTANT]
> **Arithmetic correctness** confirms that formulas evaluate without errors, zero-divisions, or artificial multiplier bugs.
> It does **NOT** guarantee **predictive accuracy**. 
> True predictive accuracy requires empirical team strength ratings (Phase 1C) and leak-free machine learning models (Phase 2B+).

---

## 6. Result
**COMPLETED SUCCESSFULLY**. All baseline arithmetic verified.
