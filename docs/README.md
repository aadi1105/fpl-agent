# FPL AI 2026/27 Decision Engine — Central Documentation

Welcome to the official documentation hub for the **FPL AI 2026/27 Decision Engine**. This directory contains comprehensive technical specifications, architectural blueprints, project roadmaps, historical phase audit reports, data pipeline guidelines, optimization formulations, and model registries.

---

## 📚 Documentation Navigation

### 1. Core Architecture & Specifications
* [**Project Overview**](PROJECT_OVERVIEW.md) — High-level objectives, decision philosophy, problem scope, and system pipeline.
* [**Technical Architecture**](ARCHITECTURE.md) — Detailed layer-by-layer technical breakdown (Ingestion, DB, Team Ratings, Engine, Optimizer, API, UI).
* [**Authoritative Roadmap**](ROADMAP.md) — Chronological roadmap of completed milestones (Phase 1–2A) and upcoming ML/AI phases.

---

### 2. Completed Phase Documentation
* [**Phase 1: Deterministic Baseline Engine**](phases/PHASE_1_BASELINE.md) — Initial FPL API ingestion, price-tier baseline metrics, MILP squad optimizer.
* [**Phase 1A: Fixture-Aware Projections**](phases/PHASE_1A_FIXTURE_PROJECTIONS.md) — Dynamic multi-gameweek projections, home/away modifiers, 2026/27 DEFCON CBIT integration.
* [**Phase 1B: Projection Arithmetic Audit**](phases/PHASE_1B_PROJECTION_AUDIT.md) — Arithmetic verification, root cause analysis of 500-rating fallback bug, component breakdown.
* [**Phase 1C: Team Strength & Fixture Context Layer**](phases/PHASE_1C_TEAM_STRENGTH.md) — Team Rating Calculator, Bayesian shrinkage, [600, 1600] rating bounds, Arsenal cap audit.
* [**Phase 2A: Historical Leak-Free ML Dataset**](phases/PHASE_2A_HISTORICAL_DATASET.md) — 110,268 player-GW records across 4 seasons, time-based splits, temporal leakage tests.
* [**Phase 2B: Expected Minutes ML Model (Planned)**](phases/PHASE_2B_EXPECTED_MINUTES.md) — Specifications for upcoming LightGBM expected minutes model.

---

### 3. Machine Learning & Model Registry
* [**Model Registry**](models/MODEL_REGISTRY.md) — Status tracking table for active baseline models vs. planned ML models.
* [**Baseline Models**](models/BASELINE_MODELS.md) — Mathematical formulations for baseline heuristics (xG/xA price tiers, Poisson DEFCON, Team Ratings).
* [**ML Models Specification**](models/ML_MODELS.md) — Planned LightGBM/XGBoost architectures for expected minutes, xG, xA, CS, and DEFCON.

---

### 4. Data Engineering & Leakage Prevention
* [**Data Dictionary**](data/DATA_DICTIONARY.md) — Schema definitions for database models and the 35 fields in `historical_minutes_dataset.csv`.
* [**Data Pipeline Architecture**](data/DATA_PIPELINE.md) — FPL API live sync, SQLite database layer, and historical dataset builder pipeline.
* [**Leakage Prevention Protocol**](data/LEAKAGE_PREVENTION.md) — Mandatory temporal rules, pre-deadline data isolation, rolling window bounds, and audit checks.

---

### 5. Mathematical Optimization
* [**Optimization Architecture**](optimization/OPTIMIZATION_ARCHITECTURE.md) — Google OR-Tools MILP formulation, 15-player squad constraints, Starting XI, Bench order.
* [**Optimization Modes**](optimization/OPTIMIZATION_MODES.md) — Single GW focus vs. 4-GW weighted horizon (`CURRENT_GW_PLUS_3`).
* [**Objective Functions**](optimization/OBJECTIVE_FUNCTIONS.md) — Exact mathematical objective functions for squad expected points maximization.

---

### 6. Strategy & Decisions
* [**Architectural Decisions Record (ADR)**](decisions/ARCHITECTURAL_DECISIONS.md) — Key architectural choices, rationale, and design principles.
* [**Development Prompts Archive**](prompts/) — Original phase instructions and specifications used during development.

---

### 🚀 Quick Start & Development Commands

```bash
# Run FastAPI Backend Server
python -m uvicorn backend.main:app --reload --port 8000

# Run Complete Automated Test Suite (27/27 Passing)
python -m pytest

# Run Historical Dataset Builder (Phase 2A)
python -m backend.ml.dataset_builder

# Run Phase 1C Verification Script
python -m scripts.verify_phase1c
```
