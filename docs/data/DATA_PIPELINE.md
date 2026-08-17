# Data Pipeline Architecture & DGW Representation

---

## 1. Live FPL API Ingestion Pipeline (`backend/ingestion/fpl_api.py`)

The live data ingestion pipeline syncs official FPL API state into local SQLite tables:

```text
Official FPL API
  ├── /bootstrap-static/ ──> Sync Teams, Gameweeks, Players
  └── /fixtures/         ──> Sync Fixture Schedule & Results
```

---

## 2. Historical ML Dataset Construction Pipeline (`backend/ml/dataset_builder.py`)

The historical ML dataset pipeline downloads raw open-source season logs across four seasons (2022/23 to 2025/26), caches raw CSVs in `data/raw/`, processes pre-deadline features chronologically, represents each match log independently per fixture, executes temporal leakage tests, and outputs the final dataset to `data/ml/historical_minutes_dataset.csv`.

```text
Raw Historical CSVs (vaastav repo)
  ├── 2022/23 (26,505 raw rows) ──> Process & Vectorize (Per Fixture) ──> 26,505 records
  ├── 2023/24 (29,725 raw rows) ──> Process & Vectorize (Per Fixture) ──> 29,725 records
  ├── 2024/25 (27,605 raw rows) ──> Process & Vectorize (Per Fixture) ──> 27,605 records
  └── 2025/26 (29,757 raw rows) ──> Process & Vectorize (Per Fixture) ──> 29,747 records
                                                                          │
                                                                          ▼
                                                          113,582 Per-Fixture Snapshots
                                                          (target_minutes max: 90 mins)
```

---

## 3. Double Gameweek (DGW) Independent Fixture Representation

> [!IMPORTANT]
> **Authoritative DGW Interface Policy**:
> Every row in `historical_minutes_dataset.csv` represents **1 single fixture ($0\text{--}90$ minutes target)**.
> DGW match logs are **NOT** aggregated into a single summed gameweek row.
> If a team plays two matches in Gameweek $N$, two separate rows are generated in the dataset:
> * **Row 1**: Player $X$, GW $N$, Fixture 1 vs Opponent A ($0\text{--}90$ mins target)
> * **Row 2**: Player $X$, GW $N$, Fixture 2 vs Opponent B ($0\text{--}90$ mins target)
>
> In the production engine (`ProjectionEngine`), `MinutesPredictor` predicts per-fixture expected minutes ($0\text{--}90$ mins). For DGWs, `ProjectionEngine.run_projections` calls `calculate_player_xp_breakdown` independently for each fixture and sums `total_xMins` and `total_xP` across both fixtures.

---

## 4. Low-Sample Player Handling Architecture

Low-sample players (players with $<180$ minutes in current DB or $<300$ historical minutes) are handled via a 3-layer architecture:

1. **Layer 1: Vectorized Rolling Feature Isolation**:
   Rolling prior features (`minutes_last_1`, `starts_last_5`, `average_minutes_last_5`) use `min_periods=1` with explicit `fillna(0)`. In Gameweek 1 of any season, prior rolling statistics are strictly reset to 0.

2. **Layer 2: Price-Tier Baseline Fallback**:
   When a player has $<180$ minutes in raw API data, `calculate_expected_minutes()` assigns a baseline estimate based on player cost tier:
   * Cost $\ge £9.0\text{m} \implies 84.0 \text{ mins}$
   * Cost $\ge £7.0\text{m} \implies 75.0 \text{ mins}$
   * Cost $\ge £5.5\text{m} \implies 65.0 \text{ mins}$
   * Cost $\ge £4.5\text{m} \implies 55.0 \text{ mins}$
   * Cost $< £4.5\text{m} \implies 35.0 \text{ mins}$

3. **Layer 3: Single-Fixture Clamping & Production Fallback**:
   In `MinutesPredictor.predict()`, predictions are strictly clamped within $[0.0, 90.0]$ per single match. If model artifacts or features are missing/invalid, `MinutesPredictor` safely invokes `get_fallback_prediction()` using deterministic baseline fallbacks with logging (`used_fallback=True`).
