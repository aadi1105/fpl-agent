# Phase 3N.24 — Fix Chip Accounting + Cumulative Points + Rank Data + Gameweek Score Validation

## Executive Summary

Phase 3N.24 fixes critical scoring, chip accounting, cumulative overall points, and rank display issues across the FPL AI Decision Engine. When a manager activates a chip (such as Bench Boost in GW2), the net Gameweek score accurately accounts for starting XI points, captain bonus, bench points, transfers cost, and chip-specific scoring rules.

---

## Key Technical Deliverables

### 1. Authoritative Gameweek Net Score Formula
Implemented in `FPLHistoryService.get_gameweek_snapshot()`:
$$\text{net\_gw\_score} = \text{starters\_raw\_pts} + \text{captain\_bonus} + \text{bench\_pts\_if\_bench\_boost} - \text{transfers\_cost}$$

For GW2 with Bench Boost active:
- Starting XI raw points: 77
- Captain bonus (B.Fernandes 23 pts): +23
- Bench points (Groß 13, Thomas 8, van Ewijk 2, Kinsky 1): 24
- Net GW2 Score: **124 PTS**

### 2. Multi-Source Used Chips Engine
Added `FPLHistoryService.get_used_chips_map(fpl_entry_id)` which inspects:
1. Official FPL history `chips` endpoint (if linked).
2. Saved immutable `GameweekTeamSnapshot` DB records.
3. Current active chip on `UserSquad`.

Exposes `used_chips_map` (e.g. `{"benchboost": 2}`) in squad APIs and renders chip status as `USED — GW2`.

### 3. Cumulative Overall Points Engine
Updated season history calculations so that overall points accumulate strictly over completed/live Gameweeks:
- GW1: 54 PTS
- GW2: 124 PTS (Cumulative Overall = 178 PTS)
- GW3+ (Upcoming): Preserves latest cumulative total of **178 PTS** (never 0 or empty).

### 4. Unlinked Manager Rank Handling
Updated `get_season_history()` to return `overall_rank = "NOT_LINKED"` when an official FPL manager ID is not linked. Frontend formats this as a clean `<span class="player-pos-badge pos-DEF">NOT LINKED</span>` badge with explanatory tooltip rather than empty dashes (`—`).

### 5. Squad Editor Used Chip Protection
Updated `openEditSquadModal()` in `frontend/index.html` to inspect `used_chips_map`. Already-used chips are disabled in the dropdown with text `Bench Boost (USED — GW2)` to prevent illegal chip reuse in future Gameweeks.

---

## Verification & Test Results

### 1. Automated Test Suite
Created `tests/test_phase3n24_chip_accounting_and_cumulative_points.py` with 11 comprehensive unit and integration tests:
- `test_bench_boost_points_are_included_in_final_score`: PASS
- `test_bench_boost_score_equals_starting_xi_plus_captain_bonus_plus_bench`: PASS
- `test_captain_bonus_is_not_double_counted`: PASS
- `test_gw2_expected_score_is_124_for_current_fixture_data`: PASS
- `test_active_chip_persists_after_refresh`: PASS
- `test_used_chip_removed_from_available_chips`: PASS
- `test_overall_points_are_cumulative`: PASS
- `test_future_gameweeks_preserve_latest_cumulative_total`: PASS
- `test_rank_is_not_fabricated_when_unavailable`: PASS
- `test_chip_state_is_gameweek_specific`: PASS
- `test_completed_snapshot_remains_immutable_after_current_squad_edit`: PASS

### 2. Full Regression Suite Run
Ran all 28 project test suites:
- **Total Tests Collected**: 137
- **Total Passed**: 137 (100% PASS RATE)
