# Data Pipeline Architecture

---

## 1. Live FPL API Ingestion Pipeline (`backend/ingestion/fpl_api.py`)

The live data ingestion pipeline syncs official FPL API state into local SQLite tables:

```text
Official FPL API
  ├── /bootstrap-static/ ──> Sync Teams, Gameweeks, Players
  └── /fixtures/         ──> Sync Fixture Schedule & Results
```

### Execution Command:
```python
from backend.database import SessionLocal
from backend.ingestion.fpl_api import FPLDataIngestion

db = SessionLocal()
ingestion = FPLDataIngestion()
synced_counts = ingestion.sync_all(db)
db.close()
```

---

## 2. Historical ML Dataset Construction Pipeline (`backend/ml/dataset_builder.py`)

The historical ML dataset pipeline downloads raw open-source season logs across four seasons (2022/23 to 2025/26), caches raw CSVs in `data/raw/`, processes pre-deadline features chronologically, aggregates Double Gameweeks into single pre-deadline snapshots, executes temporal leakage tests, and outputs the final dataset to `data/ml/historical_minutes_dataset.csv`.

```text
Raw Historical CSVs (vaastav repo)
  ├── 2022/23 (26,505 raw rows) ──> Process & Vectorize ──> 24,957 GW snapshots
  ├── 2023/24 (29,725 raw rows) ──> Process & Vectorize ──> 28,742 GW snapshots
  ├── 2024/25 (27,605 raw rows) ──> Process & Vectorize ──> 27,231 GW snapshots
  └── 2025/26 (29,757 raw rows) ──> Process & Vectorize ──> 29,338 GW snapshots
                                                               │
                                                               ▼
                                                110,268 Player-GW Snapshots
                                                (data/ml/historical_minutes_dataset.csv)
```

---

## 3. Data Quality & Audit Pipeline

Every execution of the dataset builder runs automated quality & leakage verification:
* Duplicate `(season, gameweek, player_id)` check.
* Range validation ($0 \le \text{target\_minutes} \le 240$, valid positions).
* Target logical consistency ($M \ge 60 \implies \text{target\_60\_plus} = 1$).
* GW1 zero-history check (`minutes_last_1` $== 0$).
