# Optimization Modes — Single GW vs. 4-GW Weighted Horizon

---

## 1. Single Gameweek Mode (`CURRENT_GW_ONLY`)
* **Focus**: Maximizes expected points strictly for the immediate upcoming gameweek ($GW_1$).
* **Use Case**: Wildcard activation in GW1 or one-week punt decisions.

---

## 2. Multi-Gameweek Horizon Mode (`CURRENT_GW_PLUS_3`) — DEFAULT
* **Focus**: Evaluates expected points across a 4-gameweek horizon using decaying horizon weights:
  * **GW1 Weight**: `55%` ($0.55$) — Immediate GW return priority.
  * **GW2 Weight**: `20%` ($0.20$)
  * **GW3 Weight**: `15%` ($0.15$)
  * **GW4 Weight**: `10%` ($0.10$)
* **Weighted Score Formula**:
  $$\text{Weighted\_xP}_p = 0.55 \cdot xP_{p, \text{GW1}} + 0.20 \cdot xP_{p, \text{GW2}} + 0.15 \cdot xP_{p, \text{GW3}} + 0.10 \cdot xP_{p, \text{GW4}}$$
* **Rationale**: Prevents selecting short-sighted single-week punts facing terrible upcoming fixtures while prioritizing immediate GW1 returns.
