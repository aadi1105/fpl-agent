# Phase 3N.25 — My Team Command Center UI Overhaul

## 1. Objective
Redesign the **My Team Command Center** page from a generic collection of rounded cards into a cohesive, high-density football management & match broadcast interface without regressing any underlying scoring, Gameweek history, squad persistence, chip accounting, or FPL API functionality.

---

## 2. Key Architecture & UI Refinements

1. **Compact Integrated Team Control Strip (`.team-control-strip`)**:
   - Replaced the giant `MY TEAM COMMAND CENTER` header block with a sleek, compact control strip.
   - **Left**: `MY TEAM` title + meta pill `15 PLAYERS · £0.0M BANK · 1 FT`.
   - **Center**: Matchweek timeline navigator `‹ GW2 🔴 LIVE ›` with quick-switch matchweek pills (`GW1 ✓`, `GW2 🔴 LIVE`, `GW3`, ...).
   - **Right**: Sleek primary management actions `⚙ EDIT SQUAD` and `📊 COMPARE`.

2. **Hero Football Broadcast Scoreboard Overlay (`.broadcast-scoreboard-strip`)**:
   - Transformed floating KPI boxes into a TV match broadcast scoreboard overlay banner.
   - Hero number: `124 PTS` (GW2 Live score).
   - Thin vertical divider stat strip: `CAPTAIN BONUS +23 pts` | `BENCH 24 pts` | `TRANSFERS 0 (-0pts)` | `SEASON TOTAL 178 pts` | `ACTIVE CHIP BENCH BOOST`.
   - Animated live pulse badge: `🔴 LIVE SCORING ACTIVE`.

3. **Pitch Centerpiece & Attached Substitutes Technical Strip**:
   - Football pitch remains the dominant visual hero with formation badge `3-4-3`.
   - Bench redesigned as an attached technical-area strip (`SUBSTITUTES`) directly under the pitch.

4. **Right Column Technical & Tactical Hub**:
   - **Squad Status & Financials**: Compact squad bank (`£0.0m`), free transfers (`1 FT`), and starting XI projected xP (`41.95 xP`).
   - **Transfer Intelligence**: Recommended transfer card (`CALVERT-LEWIN → WISSA +1.69 xP`).

5. **Season Chips Grid & Dense Gameweek History Log**:
   - Season chips styled as 4 compact horizontal tiles (`WILDCARD AVAILABLE`, `FREE HIT AVAILABLE`, `BENCH BOOST USED · GW2`, `TRIPLE CAPTAIN AVAILABLE`).
   - Dense broadcast Gameweek log with season summary strip (`TOTAL: 178 PTS`, `GW AVG: 89.0`, `BEST: 124 PTS`, `WORST: 54 PTS`, `RANK: NOT LINKED`, `TRANSFERS: 0`) and interactive rows.

---

## 3. Verification & Automated Test Suite

- Created dedicated test suite [`tests/test_phase3n25_my_team_ui_overhaul.py`](file:///C:/Users/RAJIV%20KUMAR/fpl-agent/tests/test_phase3n25_my_team_ui_overhaul.py).
- Ran all **142 test cases across 29 test suites** with **100% pass rate**.

```bash
python -m pytest tests/test_phase3n25_my_team_ui_overhaul.py ... (29 test files)
================= 142 passed, 4 warnings in 166.31s (0:02:46) =================
```
