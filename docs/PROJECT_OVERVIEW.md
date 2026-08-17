# Project Overview — FPL 2026/27 Decision Engine

---

## 1. Project Objective

Build a personal **Fantasy Premier League (FPL) decision-support system** that maximizes expected FPL performance over the 2026/27 season.

The system does **NOT** simply ask an LLM to generate a fantasy team.

The core principle is:

> **Numerical models predict outcomes. Structured data determines constraints. An LLM researches and interprets qualitative information. An optimizer makes the final mathematical selection.**

The system provides **explainable recommendations**, addressing:
* Who should I buy?
* Who should I sell?
* Who should I hold?
* Who should I captain / vice-captain?
* Which players are the best differentials?
* What is the mathematically optimal squad given my budget and squad constraints?
* Should I prioritize GW1 points or medium-term (4-GW) points?

---

## 2. Core Design Philosophy

```text
Do NOT build:
LLM → "Pick my FPL team"

Build:
Data → Statistical Projection → Qualitative Research → Adjustment → Optimization → Decision
```

The LLM should **NOT** calculate expected points or solve linear constraints.

### Task Separation:

#### Numerical & Mathematical Layer (Handled by Statistical Models / ML / OR-Tools):
* Expected points ($xP$)
* Expected goals ($xG$) and expected assists ($xA$)
* Clean-sheet probability ($CS\%$)
* Expected minutes ($xMins$)
* Defensive contribution probability ($DEFCON\%$)
* Bonus point probability
* Team strength & fixture difficulty modifiers
* Price / value / budget constraints
* Squad optimization (Mixed-Integer Linear Programming)

#### Qualitative & Research Layer (Handled by LLM / RAG - Future Phase):
* Extracting information from injury reports and news articles
* Interpreting manager press conference quotes
* Detecting sudden role changes or starting XI rotations
* Identifying set-piece takers
* Explaining why a recommendation changed

---

## 3. High-Level System Architecture Flowchart

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          DATA INGESTION                                │
│           Official FPL API (Players, Teams, Fixtures, Prices)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        PREDICTION ENGINE                               │
│  - Heuristic Baseline Projections (Phase 1)                            │
│  - Team Rating Calculator & Fixture Modifiers (Phase 1C)               │
│  - Expected Minutes Machine Learning Model (Phase 2B - Planned)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       FPL SCORING ENGINE                               │
│  - 2026/27 Rules (Appearance, Goals, Assists, CS, DEFCON, Bonus, Cards)│
│  - Gameweek-Specific Expected Points (GW1 to GW8)                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        SQUAD OPTIMIZER                                 │
│  - Google OR-Tools MILP Solver                                         │
│  - Constraints: £100m Budget, 15 Players, Positional Limits, Max 3/Team│
│  - Horizon Weighting: GW1 (55%), GW2 (20%), GW3 (15%), GW4 (10%)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    STARTING XI & CAPTAINCY                             │
│  - Optimal 11-player formation (Valid FPL formations)                  │
│  - Bench Order (GKP1, SUB1, SUB2, SUB3)                                │
│  - Captain (2x xP) & Vice-Captain Selection                            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     USER DASHBOARD / API                               │
│  - FastAPI REST Endpoints (`/api/v1/optimize/squad`, `/diagnostics`)   │
│  - React / Vite UI Dashboard                                           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Key Distinctions in Decision Support

1. **Prediction vs. Projection**:
   * *Prediction*: Machine learning models predicting player minutes, xG, xA, CS probability.
   * *Projection*: Combining underlying predicted rates with gameweek fixture modifiers and expected minutes to output expected points ($xP$).

2. **Squad Optimization vs. Starting XI Optimization**:
   * *Squad Optimization*: Selecting the 15-player squad (2 GKP, 5 DEF, 5 MID, 3 FWD) subject to the £100.0m budget and max 3 players per club limit.
   * *Starting XI Optimization*: Selecting the optimal 11 starters from the 15 squad members to maximize current GW points subject to legal formation rules (1 GKP, $\ge 3$ DEF, $\ge 2$ MID, $\ge 1$ FWD).

3. **Single GW vs. Multi-GW Horizon (`CURRENT_GW_PLUS_3`)**:
   * *Single GW*: Maximizes expected return strictly for the upcoming gameweek.
   * *4-GW Horizon*: Weights GW1 at 55%, GW2 at 20%, GW3 at 15%, and GW4 at 10% to ensure squad building considers upcoming fixture runs without sacrificing immediate return.
