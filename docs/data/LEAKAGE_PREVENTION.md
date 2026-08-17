# Temporal Data Leakage Prevention Protocol

---

## 1. Golden Rule of Temporal Isolation

> **FOR ANY PREDICTION SNAPSHOT REPRESENTING GAMEWEEK $N$, ALL INPUT FEATURES MUST REPRESENT INFORMATION KNOWN STRICTLY BEFORE THE GAMEWEEK $N$ DEADLINE.**
> 
> **FUTURE INFORMATION FROM GAMEWEEK $N$ OR LATER MUST NEVER INFLUENCE PRE-DEADLINE FEATURES.**

---

## 2. Leakage Prevention Guidelines

### A. Rolling Player Statistics
* Rolling features for GW $N$ (e.g. `minutes_last_1`, `minutes_last_5`, `starts_last_5`) use data from matches played in GW $< N$ ONLY.
* In Gameweek 1, all prior rolling statistics are forced to `0`. No future matches from GW1 or later are referenced.

### B. Team Strength Ratings
* Historical team attacking and defensive ratings for GW $N$ are calculated using team $xG$ and $xGA$ accumulated strictly from matches played in GW $< N$ of that season.
* Full-season final ratings are **NEVER** used for earlier gameweeks during dataset construction.

### C. Target Isolation
* Target columns (`target_started`, `target_minutes`, `target_60_plus`, `target_zero_minutes`) are strictly isolated and never included as input features.

### D. Time-Based Train / Validation / Test Splits
* Splits are strictly chronological by season:
  * **Train**: 2022/23 & 2023/24
  * **Validation**: 2024/25
  * **Test**: 2025/26
* Random cross-validation splits across time are **PROHIBITED** to prevent future matches leaking into training past matches.

---

## 3. Automated Leakage Tests ([`tests/test_phase2a_dataset.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase2a_dataset.py))

```python
def test_temporal_leakage_gw1_rolling_stats(dataset_and_metadata):
    df, meta = dataset_and_metadata
    gw1 = df[df['gameweek'] == 1]
    assert (gw1['minutes_last_1'] == 0).all()
    assert (gw1['starts_last_1'] == 0).all()
```
