# FPL 2026/27 Decision Engine

A quantitative Fantasy Premier League (FPL) decision-support system that maximizes expected points using deterministic statistical baseline models, 2026/27 scoring rules (Poisson-based DEFCON CBIT threshold points), and multi-mode Google OR-Tools Mixed-Integer Linear Programming (MILP) optimization.

> **Model Classification**: Baseline Projection Model v0.2 (Deterministic / Statistical Baseline). ML models (LightGBM/XGBoost for minutes, xG, xA, DEFCON) are in pipeline development and will be benchmarked out-of-sample before deployment.

---

## 🌟 Core Optimization Architecture (`CURRENT_GW_PLUS_3`)

The optimization engine separates 15-man squad selection from starting XI lineup optimization:

```text
Problem A (Squad Selection)
Select 15 players maximizing 4-GW Weighted Horizon Score:
0.55 × GW0 + 0.20 × GW1 + 0.15 × GW2 + 0.10 × GW3
       │
       ▼
Problem B (Starting XI Selection)
Given the 15-man squad, select 11 starting players maximizing CURRENT GAMEWEEK (GW0) xP
subject to legal formation limits (1 GKP, 3-5 DEF, 2-5 MID, 1-3 FWD)
       │
       ▼
Captain & Vice-Captain Selection
Captain selected as starting XI player with highest current-GW xP.
```

### Supported Optimization Modes
- **`CURRENT_GW_PLUS_3` (Default)**: 55% GW0, 20% GW1, 15% GW2, 10% GW3 weighted horizon.
- **`STRONG_XI_DUMP_BENCH`**: Concentrates budget on top starting XI while selecting minimal bench enablers.
- **`BALANCED_BENCH`**: Starting XI xP + bench minutes security.
- **`MAXIMUM_SQUAD`**: Equal 25% weight across 4-GW horizon.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database & Sync Live FPL Data
```bash
python -m backend.init_db
```

### 3. Run Web Application Server
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 🧪 Test Suite

Run unit tests covering models, projections, 2-step optimizer, and API routes:
```bash
python -m pytest tests/
```

---

## 📄 License
MIT License
