# PHASE 3I — FULL-POOL CALIBRATED PROJECTION SANITY AUDIT

OBJECTIVE:
Perform a READ-ONLY full-pool sanity audit of expected_xp_calibrated_v1 across all active 2026/27 GW1 players (~590 players) before squad optimization is allowed to run.

DO NOT modify the calibration model.
DO NOT retrain any model.
DO NOT modify the optimizer.
DO NOT add ownership or consensus adjustments.
DO NOT change projections.

Key evaluation criteria:
1. Full population audit (~590 active players).
2. Positional & Price tier distribution breakdown.
3. Top 30 Calibrated GW1 players.
4. Bottom / Outlier adjustment audit (top 10 positive & top 10 negative adjustments).
5. Premium player sanity check (Haaland, Bruno, Saka, Palmer, João Pedro, Calvert-Lewin, Marmoush, Isak, Watkins, Son).
6. Defender / GK sanity check (O'Reilly, Gvardiol, Calafiori, Gabriel, Raya, Pope).
7. Minutes sanity check (P(start) >= 0.90 & E[mins] >= 82).
8. Low-sample audit (<300 historical minutes in top 100).
9. Transfer / current-club sanity check (Awoniyi, Nelson, transferred players).
10. Fixture sensitivity check.
11. Calibration monotonicity & numerical sanity.
12. FPL Price Integrity.
13. Frontend audit.
14. Raw Top 20 vs Calibrated Top 20 comparison table.
15. 10 Explicit Safety Check Questions.
16. Final Deployment Decision: SAFE FOR OPTIMIZATION / NOT SAFE FOR OPTIMIZATION.
