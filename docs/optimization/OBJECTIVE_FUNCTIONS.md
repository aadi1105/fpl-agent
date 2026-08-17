# Mathematical Objective Functions

---

## 1. Primary MILP Objective Function

Let $x_p \in \{0, 1\}$ be the binary variable indicating whether player $p$ is selected in the 15-player squad.
Let $s_p \in \{0, 1\}$ be the binary variable indicating whether player $p$ is selected in the Starting XI.
Let $c_p \in \{0, 1\}$ be the binary variable indicating whether player $p$ is selected as Captain.

The objective function maximizes total weighted expected points across the starting XI and captain bonus:

$$\text{Maximize } Z = \sum_{p \in P} s_p \cdot \text{Weighted\_xP}_p + \sum_{p \in P} c_p \cdot xP_{p, \text{GW1}}$$

where:
* $\text{Weighted\_xP}_p = 0.55 \cdot xP_{p, \text{GW1}} + 0.20 \cdot xP_{p, \text{GW2}} + 0.15 \cdot xP_{p, \text{GW3}} + 0.10 \cdot xP_{p, \text{GW4}}$
* $c_p \cdot xP_{p, \text{GW1}}$ represents the additional $+1\times$ captain bonus earned in GW1.

---

## 2. Key Constraints Formulations

1. **Starter Constraint**: $s_p \le x_p \quad \forall p$
2. **Captain Starter Constraint**: $c_p \le s_p \quad \forall p$
3. **Total Starters**: $\sum_{p \in P} s_p = 11$
4. **Total Captain**: $\sum_{p \in P} c_p = 1$
5. **Budget Limit**: $\sum_{p \in P} x_p \cdot \text{cost}_p \le 1000$
6. **Club Limit**: $\sum_{p \in \text{Team}_t} x_p \le 3 \quad \forall t \in \{1 \dots 20\}$
