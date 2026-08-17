# Architectural Decisions Record (ADR)

---

### ADR 001: Separate Prediction from Optimization
* **Status**: ACCEPTED
* **Decision**: Machine learning models and statistical engines predict individual outcomes ($xMins, xG, xA, CS\%$). Linear programming (OR-Tools MILP) makes squad selections.
* **Rationale**: LLMs and end-to-end neural networks hallucinate budget rules and positional constraints. Mathematical solvers guarantee 100% legal squad compliance.

---

### ADR 002: Separate Squad Selection from Starting XI Selection
* **Status**: ACCEPTED
* **Decision**: Solve 15-player squad constraints (£100m budget, max 3/club) simultaneously with 11-player starting formation and captaincy.
* **Rationale**: Ensures bench players provide valid position coverage while starting XI maximizes current GW return.

---

### ADR 003: Multi-Gameweek Horizon Weighting (`CURRENT_GW_PLUS_3`)
* **Status**: ACCEPTED
* **Decision**: Apply decaying weights (GW1: 55%, GW2: 20%, GW3: 15%, GW4: 10%) across a 4-GW window.
* **Rationale**: Prioritizes immediate GW1 return while building a squad resilient to upcoming fixture runs.

---

### ADR 004: Preservation of Deterministic Baseline
* **Status**: ACCEPTED
* **Decision**: Maintain the Phase 1C deterministic/statistical baseline as the active production engine.
* **Rationale**: Planned ML models must beat baseline performance out-of-sample before replacing baselines.

---

### ADR 005: Strict Temporal Data Isolation (Zero Data Leakage)
* **Status**: ACCEPTED
* **Decision**: In historical ML dataset construction (Phase 2A), all features for GW $N$ must use data strictly from GW $< N$.
* **Rationale**: Prevents lookahead bias and guarantees out-of-sample validity when training predictive models.

---

### ADR 006: Specialized Predictive ML Models Over Single LLM
* **Status**: ACCEPTED
* **Decision**: Train dedicated gradient-boosted models for specific targets ($xMins, xG, xA$) rather than prompting LLMs for points predictions.
* **Rationale**: Specialized numerical models achieve lower MAE and higher statistical precision.
