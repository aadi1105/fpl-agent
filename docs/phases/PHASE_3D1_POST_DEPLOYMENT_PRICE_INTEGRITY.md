# Phase 3D.1: Post-Deployment Player Price Integrity Audit & Fix

## Executive Summary
Following Phase 3D deployment, a post-deployment price integrity audit was conducted to investigate an apparent discrepancy where Bruno Fernandes was reported at £7.0m / 9.3% ownership in diagnostic reporting tables instead of his canonical 2026/27 FPL price of £12.0m / 48.6% ownership.

The read-only audit across all 590 active database players revealed that:
1. **Canonical Database Source**: `Player.now_cost` in `fpl_engine.db` is the single source of truth (`now_cost = 120` $\to$ £12.0m).
2. **System Layers Reconciliation**:
   - Projection Engine: 590 / 590 players match `Player.now_cost` (0 mismatches).
   - Squad Optimizer: 100% match `Player.now_cost` (0 mismatches).
   - REST API Endpoints (`/api/v1/projections/diagnostics`): 100% match `Player.now_cost` (0 mismatches).
   - Frontend Display: 100% match `Player.now_cost / 10.0` (0 mismatches).
3. **Root Cause of Diagnostic Report Mismatch**:
   In the reporting script (`scratch/run_phase3d_projections_and_diagnostics.py`), target player filtering relied on substring search (`df['web_name'].str.contains('Bruno Fernandes')`). In the official FPL API, Bruno Fernandes' `web_name` is stored as `B.Fernandes`. The substring search returned empty, and secondary matching on `'Bruno'` selected `Bruno G.` (Bruno Guimarães, ID 452, £7.0m, 9.3% ownership) instead of `B.Fernandes` (ID 426, £12.0m, 48.6% ownership).
4. **Resolution**:
   Updated reporting script matching to use explicit canonical Player IDs (`id == 426`), ensuring 100% canonical database accuracy.

---

## Canonical Price & Ownership Audit for 12 Critical Diagnostic Players

| Player | Position | Canonical Player ID | Canonical `now_cost` | Canonical Price (£m) | Canonical Ownership (%) | GW0 xP (v2) | Model v2 Rank |
|---|---|---|---|---|---|---|---|
| **Erling Haaland** | FWD | 411 | 155 | £15.5m | 71.4% | 1.47 | #536 |
| **Bruno Fernandes** | MID | 426 | 120 | £12.0m | 48.6% | 2.01 | #293 |
| **Cole Palmer** | MID | 154 | 95 | £9.5m | 10.7% | 1.99 | #316 |
| **Bukayo Saka** | MID | 12 | 95 | £9.5m | 9.9% | 2.22 | #262 |
| **Gabriel Magalhães** | DEF | 4 | 80 | £8.0m | 28.4% | 4.18 | #17 |
| **Bryan Mbeumo** | MID | 427 | 80 | £8.0m | 29.5% | 2.01 | #293 |
| **Antoine Semenyo** | MID | 397 | 85 | £8.5m | 26.9% | 2.03 | #275 |
| **Omar Marmoush** | FWD | 401 | 70 | £7.0m | 0.8% | 1.25 | #582 |
| **Taiwo Awoniyi** | FWD | 492 | 55 | £5.5m | 0.5% | 1.28 | #578 |
| **William Osula** | FWD | 465 | 60 | £6.0m | 1.1% | 1.23 | #584 |
| **João Pedro** | FWD | 165 | 75 | £7.5m | 59.0% | 1.47 | #536 |
| **Dominic Calvert-Lewin** | FWD | 346 | 60 | £6.0m | 26.5% | 1.48 | #534 |

---

## Regression Test Verification
Regression tests in `tests/test_price_integrity.py` explicitly verify:
- `test_bruno_fernandes_canonical_price_and_ownership`: Verifies `B.Fernandes` (ID 426) has `now_cost == 120` (£12.0m) and `selected_by_percent == 48.6%`.
- `test_all_590_players_exact_single_canonical_price`: Verifies all 590 active DB players have a valid canonical price.
- `test_api_payload_price_matches_canonical_now_cost`: Verifies REST API diagnostic endpoint payload prices match `Player.now_cost`.
- `test_optimizer_and_frontend_payload_price_integrity`: Verifies squad optimizer return payloads match `Player.now_cost` and `now_cost_str`.
