# Squad & Starting XI Optimization Architecture

---

## 1. Overview

The decision-support engine uses **Mixed-Integer Linear Programming (MILP)** powered by **Google OR-Tools** to select the mathematically optimal 15-player squad, 11-player starting formation, bench order, and captaincy picks.

---

## 2. Hard Constraints Enforced

1. **Total Budget**:
   $$\sum_{p \in \text{Squad}} \text{cost}_p \le £100.0\text{m} \quad (1000 \text{ in tenths})$$
2. **Squad Size & Positions**:
   * Total squad size = 15 players
   * Exactly 2 Goalkeepers (`GKP`)
   * Exactly 5 Defenders (`DEF`)
   * Exactly 5 Midfielders (`MID`)
   * Exactly 3 Forwards (`FWD`)
3. **Club Limit**:
   * Maximum 3 players per Premier League team.
4. **Starting XI Constraints**:
   * Exactly 11 starters.
   * Exactly 1 Goalkeeper.
   * At least 3 Defenders ($\text{DEF} \ge 3$).
   * At least 2 Midfielders ($\text{MID} \ge 2$).
   * At least 1 Forward ($\text{FWD} \ge 1$).
5. **Captaincy Constraints**:
   * Exactly 1 Captain (earns $2\times xP$).
   * Exactly 1 Vice-Captain (must be a starter, different from Captain).

---

## 3. Implementation Code Reference

Implementation: [`backend/optimizer/squad_optimizer.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/optimizer/squad_optimizer.py)
