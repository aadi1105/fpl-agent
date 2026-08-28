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
| **Phase 2C** | Expected Minutes Validation & Production Integration | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3A** | Expected Goals ($xG$) ML Model (`xg_v1_lgbm`) | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3B** | Expected Assists ($xA$) ML Model (`xa_v1_lgbm`) | **COMPLETED (DEPLOYED)** | August 2026 |
| **Pre-Phase 3C Audit** | Projection Pipeline, Current Roster & Frontend Reconciliation | **COMPLETED** | August 2026 |
| **Role Calibration** | Expected Minutes Role Evidence & Transfer Calibration | **COMPLETED (DEPLOYED)** | August 2026 |
| **Optimizer Audit** | Optimizer Modes, Progress Tracking & Positional Value Audit | **COMPLETED (DEPLOYED)** | August 2026 |
| **Price Audit** | Full 2026/27 Player Price Data Integrity Audit & Scale Validation | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3C** | Clean Sheet (`cs_v1_lgbm`) & DEFCON (`defcon_v1_poisson`) ML Models | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3C.5** | Model vs FPL Consensus Audit | **COMPLETED (AUDITED)** | August 2026 |
| **Phase 3C.6** | Expected Minutes, Role & Sample-Size Sanity Audit | **COMPLETED (AUDITED)** | August 2026 |
| **Phase 3C.7** | Temporal / Recency & Current-Form Audit | **COMPLETED (AUDITED)** | August 2026 |
| **Phase 3C.8** | Low-Sample Minutes & Per-90 Shrinkage Implementation | **COMPLETED (VALIDATED)** | August 2026 |
| **Phase 3D** | Production Model Validation, Retraining & Deployment | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3D.1** | Post-Deployment Player Price Integrity Audit & Fix | **COMPLETED (AUDITED)** | August 2026 |
| **Phase 3D.2** | Production Projection & Fixture Pipeline Forensic Audit | **COMPLETED (AUDITED)** | August 2026 |
| **Phase 3D (Reality Check)**| Prediction Reality Check (Out-of-Sample Ground-Truth Evaluation)| **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3E** | 2026/27 Current-State Player, Transfer & Fixture Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3F** | GW1 Prediction Decision & Forensic Component Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3G** | Cross-Position xP Calibration & Value Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3H** | Prediction Calibration Layer (`expected_xp_calibrated_v1`) | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3I** | Full-Pool Calibrated Projection Sanity Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3J** | Attacking Role, Price-Tier & FPL Scoring Hierarchy Audit | **COMPLETED (AUDITED)** | August 2026 |
| **Phase 3K** | Piecewise & Role-Aware Calibration (`expected_xp_calibrated_v2`) | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3K.1** | Metric Reproduction & Deployment-Gate Verification | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3L** | Optimizer Integration & Projection Consumption Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3M** | Dynamic Gameweek State & Current Player Data Refresh | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3M.1** | Gameweek Transition, Weekly Refresh & Optimizer UX Foundation | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3N.1** | Decision Engine Reality Audit & Current-State Validation | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.2** | GW2 Reality, Player-Role & User-Decision Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.2A**| My Team Functionality + Frontend UX Repair | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3N.2B**| Live Frontend Verification + Optimizer Performance Repair | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.3** | Optimization Mode Integrity & Practical Team Comparison | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.4** | Gameweek Index / Projection Consistency + Optimal XI Audit + Player Visuals | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.5** | Calibration Audit + My Team Persistence Fix | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.6** | My Team Loading UX + SQLite Concurrency / Optimizer Failure | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.7** | My Team Financial State + Legal Transfer Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.8** | My Team Persistence / Reload / Default-Squad Root-Cause Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.9** | My Team V2: Dedicated FPL-Style Team Page + Position Picker | **COMPLETED (DEPLOYED)** | August 2026 |
| **Phase 3N.10**| My Team Player Interaction + Substitution Flow | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.10B**| Player Insight Modal Close Fix & Live Verification | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.10C**| Optimizer & My Team State Isolation | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.11**| Optimization Mode Integrity + Decision Engine Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.12**| Expected-Minutes Competition + Live Data Freshness Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.13**| Long-Horizon Integrity + Diagnostics Rendering Audit | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.14**| Expected-Points Model Audit + Full UI/UX Redesign | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.15**| Production Regression Debug + Real Browser Acceptance | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.16**| My Team Command Center: Squad Management Entry Point | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.17**| My Team Squad Persistence + Rendering Failure | **COMPLETED (VERIFIED)** | August 2026 |
| **Phase 3N.18**| My Team Substitution Flow + State Reliability Fix | **COMPLETED (VERIFIED)** | August 2026 |

---

## 📑 Completed Phases Detail

### Phase 3N.18 — My Team Substitution Flow + State Reliability Fix
* Resolved second-interaction modal dead click bug by clearing inline display/visibility styles prior to `.open` activation.
* Deployed FPL-style clean substitution selection UX (`[↔️ SUBSTITUTE]` -> candidate cards grid with `[← BACK]` and `[CANCEL]`).
* Enforced formation validation with locked status cards and concise feedback.
* Implemented captain auto-transfer when benching a captain.
* Added test suite [`tests/test_phase3n18_substitution_ux_and_state.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n18_substitution_ux_and_state.py) (98/98 total tests passing).
* Zero changes made to ML models or optimizer code.
* Full details in [`docs/phases/PHASE_3N18_MY_TEAM_SUBSTITUTION_FLOW_AND_STATE_RELIABILITY_FIX.md`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/docs/phases/PHASE_3N18_MY_TEAM_SUBSTITUTION_FLOW_AND_STATE_RELIABILITY_FIX.md).
