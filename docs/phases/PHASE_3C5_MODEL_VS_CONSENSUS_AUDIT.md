# PHASE 3C.5 — MODEL vs FPL CONSENSUS AUDIT REPORT

**Phase**: 3C.5  
**Status**: COMPLETED (Read-Only Diagnostic Audit)  
**Date**: August 2026  
**Scope**: Model xP and Rank vs External FPL Consensus & Ownership (`selected_by_percent`)  

---

## Executive Summary

Phase 3C.5 establishes a strictly read-only, non-mutating empirical audit framework comparing production model projections against official FPL market consensus across 590 active 2026/27 Premier League players.

> [!NOTE]
> **Strict Guardrail Compliance**: Neither model xG/xA/CS/DEFCON prediction models, expected minutes logic, player projections, nor MILP optimizer objective functions were altered during this phase.

---

## Key Diagnostic Findings

### 1. Targeted Forward Audit
* **Haaland (MCI, £15.5m)**: Model Rank #1 | Consensus Rank #1 (71.4% ownership) | Model xP: 8.24 pts. Perfect agreement.
* **João Pedro (CHE, £7.5m)**: Model Rank #11 | Consensus Rank #2 (59.0% ownership) | Rank Gap -9 | Model xP: 4.31 pts (xG 0.41, xA 0.15). **Classification**: `A. Legitimate Model Differential / Template Value Bias`. High ownership driven by template pricing rather than elite per-match xG.
* **Calvert-Lewin (LEE, £6.0m)**: Model Rank #22 | Consensus Rank #3 (26.5% ownership) | Rank Gap -19 | Model xP: 3.48 pts (xG 0.28, xA 0.17). **Classification**: `A. Legitimate Model Differential / Template Enabler Bias`. Popular cheap enabler, but underlying model xG/xA rates remain modest.
* **Awoniyi (NFO, £5.5m)**: Model Rank #3 | Consensus Rank #43 (0.5% ownership) | Rank Gap +40 | Model xP: 5.66 pts (xG 0.63, xA 0.20). **Classification**: `C. Expected-Minutes / Role Issue (High Per-90 Extrapolation Risk)`. Strong historic per-90 rates generate high xP when projected for starter minutes.
* **Osula (NEW, £6.0m)**: Model Rank #7 | Consensus Rank #29 (1.1% ownership) | Rank Gap +22 | Model xP: 5.13 pts (xG 0.54, xA 0.15). **Classification**: `C. Expected-Minutes / Role Issue (Squad Depth / Rotation Risk)`.

### 2. Disagreement Taxonomy
1. **Category A (Legitimate Model Differential)**: FPL template picks where market ownership is disproportionately higher than model xG/xA projections (e.g. João Pedro, Calvert-Lewin).
2. **Category B (High Model Differential Opportunity)**: High model xP players under-owned by the FPL consensus (e.g. Beto, Marmoush).
3. **Category C (Expected-Minutes / Role Risk)**: Players with high per-90 efficiency rates whose projected minutes require refined role damping (e.g. Awoniyi, Osula).

---

## System Integration & Deliverables

1. **API Endpoint**: Added `/api/v1/projections/consensus_audit` returning player xP, model rank, consensus rank, ownership %, and classification.
2. **Frontend Diagnostic UI**: Added `"MODEL vs FPL CONSENSUS AUDIT"` card marked `DIAGNOSTIC ONLY` with position filtering in `index.html`.
3. **Automated Test Suite**: Added 5/5 passing regression tests in `tests/test_phase3c5_consensus_audit.py`.

---

## Verification & Test Results

* `tests/test_phase3c5_consensus_audit.py`: **5 / 5 passed (100%)**
* Full Engine Test Suite: **67 / 67 passed (100%)**
