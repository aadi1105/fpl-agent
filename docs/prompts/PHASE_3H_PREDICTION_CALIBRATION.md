# PHASE 3H — PREDICTION CALIBRATION LAYER

OBJECTIVE:
Fix the empirically demonstrated cross-position xP calibration problems identified in Phase 3G.

DO NOT modify the optimizer yet.
DO NOT manually boost Haaland, Bruno, Saka, or any other player.
DO NOT use ownership or FPL consensus as a prediction target.
DO NOT hard-code positional bonuses.

Historical predictions → actual historical outcomes must be used to learn a leak-free calibration transformation evaluated out-of-sample on a strictly chronological split:
- TRAIN: 2022/23 + 2023/24
- VALIDATE: 2024/25
- TEST (Untouched until finalization): 2025/26
