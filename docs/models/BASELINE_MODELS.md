# Baseline Models Documentation

---

## 1. Expected Minutes Baseline (`minutes_v0_baseline`)

Calculates player expected minutes based on injury status, chance of playing, total past minutes, and price tier.

```python
if status in ["i", "u", "s"]:
    expected_mins = 0.0
elif chance_of_playing_next_round is not None:
    expected_mins = avg_mins * (chance_of_playing_next_round / 100.0)
```

---

## 2. Team Strength Ratings (`team_ratings_v0`)

Calculates deterministic team attack and defence ratings scaled relative to a $1000.0$ league-average baseline.

* **Convention**: Higher Defensive Rating = BETTER defence (harder to score against, lower xGA).
* **Bayesian Shrinkage**: $w = \frac{\text{games}}{\text{games} + 5.0}$ regresses small samples toward $1000.0$.
* **Clamping**: Clamped to $[600.0, 1600.0]$. Home $+5\%$, Away $-5\%$.

---

## 3. Poisson DEFCON Model (`defcon_v0_poisson`)

Defenders receive +2 points in 2026/27 for reaching $\ge 10$ CBIT (Clearances, Blocks, Interceptions, Tackles).
The probability of reaching 10+ CBIT in a match is modeled via Poisson cumulative distribution:

$$P(\text{CBIT} \ge 10 \mid \lambda) = 1.0 - \sum_{k=0}^{9} \frac{\lambda^k e^{-\lambda}}{k!}$$

where $\lambda = \text{cbit90} \times \left(\frac{\text{xMins}}{90}\right) \times \text{cbit\_multiplier}$.
