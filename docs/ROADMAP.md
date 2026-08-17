# Authoritative Roadmap — FPL 2026/27 Decision Engine

---

## 📅 Status Overview

| Phase | Description | Status | Completion Date |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Baseline Projection Engine & MILP Optimizer | **COMPLETED** | August 2026 |
| **Phase 1A** | Fixture-Aware Gameweek Projections & UI | **COMPLETED** | August 2026 |
| **Phase 1B** | Projection Component Sanity Audit | **COMPLETED** | August 2026 |
| **Phase 1C** | Team Strength & Fixture Context Layer | **COMPLETED** | August 2026 |
| **Phase 2A** | Historical Leak-Free ML Dataset Construction | **COMPLETED** | August 2026 |
| **Phase 2B** | Expected Minutes ML Models ($P(\text{start})$, $E[\text{mins}]$, $P(60+)$, $P(0)$) | **COMPLETED (EVALUATED)** | August 2026 |
| **Phase 3** | Expected Goals ($xG$) & Expected Assists ($xA$) ML Models | 🔴 **PLANNED** | Future |
| **Phase 4** | Clean Sheet & DEFCON ML Models | 🔴 **PLANNED** | Future |
| **Phase 5** | Model Ensemble & Uncertainty Quantification | 🔴 **PLANNED** | Future |
| **Phase 6** | News, RAG & Manager Presser Agent | 🔴 **PLANNED** | Future |
| **Phase 7** | Mini-League Game Theory & Ownership Optimization | 🔴 **PLANNED** | Future |

---

## 📑 Completed Phases Detail

### Phase 2B: Expected Minutes ML Models
* Trained, backtested, and calibrated four ML models ($P(\text{start})$, Expected Minutes, $P(60+)$, $P(0)$) using LightGBM and Logistic/Ridge baselines.
* Selection performed on Validation set (2024/25); single evaluation performed on untouched Test set (2025/26).
* ML models beat baseline heuristics out-of-sample across all 4 tasks (e.g. $P(\text{start})$ LogLoss: `0.2568` vs `0.3561` baseline).
* Production projection engine **not** replaced yet, awaiting explicit integration deployment approval.
