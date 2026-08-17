# System Architecture — FPL 2026/27 Decision Engine

---

## 1. Overview & Data Flow

The system architecture consists of a Python FastAPI backend, a SQLite database layer, a deterministic projection engine, a MILP optimizer powered by Google OR-Tools, and a React/Vite dashboard.

```text
Data Ingestion → Database → Fixture Context → Team Strength Ratings → Player Projection Engine → Expected Points → Squad Optimizer → Starting XI Optimizer → Captaincy → API → Dashboard
```

---

## 2. Component Breakdowns

### A. Data Ingestion Layer (`backend/ingestion/fpl_api.py`)
* **Purpose**: Fetches live player, team, fixture, and gameweek data from the official FPL API endpoints (`/bootstrap-static/`, `/fixtures/`).
* **Inputs**: FPL API endpoints.
* **Outputs**: Database records synced to SQLite tables (`teams`, `players`, `gameweeks`, `fixtures`).
* **Current Implementation**: Fully operational synchronous request session with rate limiting and timeout handling.
* **Source Files**: [`backend/ingestion/fpl_api.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ingestion/fpl_api.py)

---

### B. Database & Schema Layer (`backend/database.py`, `backend/models.py`)
* **Purpose**: Stores historical and current season state, fixture schedules, team strength ratings, and player projections.
* **Inputs**: Ingested FPL data and computed model projections.
* **Outputs**: SQLAlchemy ORM objects (`Team`, `Player`, `Gameweek`, `Fixture`, `PlayerProjection`, `UserSquad`).
* **Current Implementation**: SQLite database (`fpl_engine.db`) with SQLAlchemy ORM session management.
* **Source Files**: [`backend/database.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/database.py), [`backend/models.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/models.py)

---

### C. Team Strength Rating Calculator (`backend/projections/team_ratings.py`)
* **Purpose**: Calculates deterministic home/away attacking and defensive ratings for all 20 Premier League teams based on team xG and xGA per match.
* **Inputs**: Aggregated player underlying metrics from database (`expected_goals`, `expected_goals_conceded`, `minutes`).
* **Outputs**: Updated team rating fields on `Team` model (`strength_attack_home`, `strength_attack_away`, `strength_defence_home`, `strength_defence_away`).
* **Formula**:
  $$\text{obs\_att} = 1000 \times \frac{\text{xG\_pg}}{\text{avg\_league\_xg}}, \quad \text{obs\_def} = 1000 \times \frac{\text{avg\_league\_xga}}{\text{xGA\_pg}}$$
  Bayesian shrinkage $w = \frac{\text{games}}{\text{games} + 5.0}$ toward $1000.0$ baseline. Clamped to $[600.0, 1600.0]$. Home $+5\%$, Away $-5\%$.
* **Convention**: Higher Defensive Rating = BETTER defence (harder to score against, lower xGA).
* **Source Files**: [`backend/projections/team_ratings.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/team_ratings.py)

---

### D. Player Projection Engine (`backend/projections/engine.py`)
* **Purpose**: Computes gameweek-specific expected points ($xP$) and detailed component breakdowns for all players across GW1–GW8.
* **Inputs**: Player underlying per-90 metrics, expected minutes, team ratings, fixture schedule.
* **Outputs**: Gameweek $xP$, breakdown dicts, and `PlayerProjection` database records.
* **Components Computed**:
  1. *Appearance Points*: 2 pts ($\ge 60$ mins) or 1 pt ($<60$ mins).
  2. *Goals & Assists*: $xG \times \text{att\_modifier} \times \text{goal\_val} + xA \times \text{att\_modifier} \times 3.0$.
  3. *Clean Sheet Points*: $CS\% \times \text{cs\_val}$ where $CS\% = \text{clamp}(0.32 \times \text{cs\_ratio}, 0.04, 0.75)$.
  4. *DEFCON Points (2026/27 Rule)*: Defenders gaining 2 pts for $\ge 10$ CBIT, modeled via Poisson probability $P(X \ge 10 \mid \lambda = \text{cbit\_match})$.
  5. *Goalkeeper Saves*: $( \text{saves\_match} / 3 ) \times 1.0$.
  6. *Bonus & Cards*: Expected bonus points and card risk deduction ($-0.10$).
* **Source Files**: [`backend/projections/engine.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/projections/engine.py)

---

### E. Squad & Starting XI Optimizer (`backend/optimizer/squad_optimizer.py`)
* **Purpose**: Solves the 15-player squad selection, 11-player starting formation, bench ordering, and captaincy choice to maximize total expected return.
* **Inputs**: Player projections, budget (£100.0m), optimization mode.
* **Outputs**: Dictionary with `starting_11`, `bench`, `captain`, `vice_captain`, `total_cost`, `weighted_horizon_xp`, and `explanations`.
* **Technology**: Google OR-Tools MILP (CBC / SCIP solver).
* **Source Files**: [`backend/optimizer/squad_optimizer.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/optimizer/squad_optimizer.py)

---

### F. Historical ML Dataset Pipeline (`backend/ml/dataset_builder.py`)
* **Purpose**: Builds a leak-free pre-deadline historical dataset across seasons 2022/23 to 2025/26 for ML model training.
* **Inputs**: Raw historical FPL season CSVs from vaastav repository.
* **Outputs**: `data/ml/historical_minutes_dataset.csv` (110,268 rows) and `data/ml/dataset_metadata.json`.
* **Source Files**: [`backend/ml/dataset_builder.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/ml/dataset_builder.py)

---

### G. API & Web UI Layer (`backend/main.py`, `frontend/`)
* **Purpose**: RESTful endpoints exposing projections, diagnostics, optimization, and data ingestion. React dashboard visualization.
* **Source Files**: [`backend/main.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/backend/main.py), [`frontend/index.html`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/frontend/index.html)
