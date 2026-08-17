# FPL 2026/27 Decision Engine

## Product & Technical Planning Document — V1

### 1. Project Objective

Build a personal Fantasy Premier League decision-support system that maximizes expected FPL performance over the season.

The system should NOT simply generate a fantasy team using an LLM.

The core principle is:

> **Numerical models predict outcomes. Structured data determines constraints. An LLM researches and interprets qualitative information. An optimizer makes the final mathematical selection.**

The system should ultimately answer:
* Who should I buy?
* Who should I sell?
* Who should I hold?
* Who should I captain?
* Which players are the best differentials?
* What is my optimal squad?
* Should I prioritize GW1 points or medium-term points?
* What transfers maximize expected points over the next 5–8 GWs?
* How does my squad compare against elite-manager consensus?
* How risky is a recommendation?
* What new information caused a recommendation to change?

The system must provide **explainable recommendations**, not black-box predictions.

---

### 2. Core Design Philosophy

Do NOT build:
`LLM → "Pick my FPL team"`

Build:
`Data → Statistical Projection → Qualitative Research → Adjustment → Optimization → Decision`

The LLM should NOT be responsible for calculating expected points.

The LLM should be responsible for:
* extracting information from articles
* interpreting manager quotes
* detecting injuries
* identifying changes in player role
* identifying likely starting XI changes
* identifying set-piece takers
* identifying transfer-related role changes
* assessing minutes confidence
* summarizing conflicting information
* explaining why a recommendation changed

Numerical models should handle:
* expected points
* expected goals
* expected assists
* clean-sheet probability
* minutes
* defensive contribution probability
* bonus probability
* fixture difficulty
* price/value
* ownership
* transfer value
* squad optimization

---

### 3. Target Architecture

Use Python for the data/model layer and LangGraph for orchestration.

```text
                         ┌─────────────────────────┐
                         │       FPL API           │
                         │ players / fixtures      │
                         │ prices / ownership      │
                         │ GW data / histories     │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │     DATA INGESTION      │
                         │                         │
                         │ API collector           │
                         │ Historical database     │
                         │ Fixture database        │
                         └────────────┬────────────┘
                                      │
             ┌────────────────────────┼──────────────────────┐
             │                        │                      │
             ▼                        ▼                      ▼
    ┌────────────────┐      ┌────────────────┐      ┌────────────────┐
    │ Projection     │      │ News Research  │      │ Fixture        │
    │ Engine         │      │ Agent          │      │ Engine         │
    │                │      │                │      │                │
    │ xP             │      │ injuries       │      │ difficulty     │
    │ xMins          │      │ lineups        │      │ fixture runs   │
    │ xG/xA          │      │ role changes   │      │ home/away      │
    │ CS             │      │ set pieces     │      │ blanks/doubles │
    │ bonus          │      │ pressers       │      │                │
    └───────┬────────┘      └───────┬────────┘      └───────┬────────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                         ┌────────────────────────┐
                         │  PLAYER STATE ENGINE   │
                         │                        │
                         │ xP                    │
                         │ minutes confidence    │
                         │ role confidence       │
                         │ injury confidence     │
                         │ fixture score          │
                         │ ownership              │
                         │ risk                   │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │  PROJECTION ENSEMBLE   │
                         │                        │
                         │ FPL Review             │
                         │ FFS RMT                │
                         │ FF Fix                 │
                         │ Internal model         │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │   SQUAD OPTIMIZER      │
                         │                        │
                         │ £100m                  │
                         │ 15 players             │
                         │ position constraints   │
                         │ max 3/team             │
                         │ formation              │
                         │ bench                   │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ DECISION ENGINE        │
                         │                        │
                         │ BUY / HOLD / SELL      │
                         │ CAPTAIN / VC           │
                         │ DIFFERENTIAL           │
                         │ TRANSFER PLAN          │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │       DASHBOARD        │
                         └────────────────────────┘
```

---

### 4. Phase 1 — MVP

The first milestone is:
> **Given a squad and a GW, produce ranked players, projected points, captaincy recommendations and optimal transfer suggestions.**

#### MVP features
1. FPL API ingestion
2. Player database
3. Fixture database
4. Historical player statistics
5. Basic expected-points model
6. Fixture-adjusted projections
7. Minutes-confidence system
8. Squad optimizer
9. Captaincy optimizer
10. Basic news/RAG layer
11. Recommendation explanations
12. Simple web dashboard

---

### 5. 2026/27 Scoring Rules

Defensive contribution points remain important in 2026/27. Defenders receive two points for reaching the required CBIT threshold in a match, with a cap of two points.
The 2026/27 BPS removes the previous BPS punishment for being tackled and adjusts the relationship between defensive contributions and bonus points.

---

### 6. Immediate Task Focus (Section 41)

Implement:
1. Python backend
2. Database (SQLite/PostgreSQL)
3. FPL API client
4. Player/Team/Fixture models
5. Data ingestion pipeline
6. Historical snapshot system
7. Basic projection engine
8. OR-Tools squad optimizer
9. FastAPI endpoints
10. Minimal React / Vite dashboard

The first demonstrable milestone:
> **"Give the system £100m and a gameweek; it returns the mathematically optimal legal squad according to our current projection model."**
