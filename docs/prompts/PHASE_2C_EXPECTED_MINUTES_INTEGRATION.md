# Phase 2C Prompt: Expected Minutes Validation & Production Integration

```text
FPL AI — PHASE 2C: EXPECTED MINUTES VALIDATION & PRODUCTION INTEGRATION

OBJECTIVE:
Audit the trained Phase 2B Expected Minutes ML models, verify test-set temporal integrity, perform calibration & player-level sanity checks, build a production inference wrapper with automatic fallback, integrate ML expected minutes into the ProjectionEngine without double-counting, update API diagnostics, and document the deployment decision.

REQUIREMENTS:
1. Audit Phase 2B models & verify zero 2025/26 test-set leakage.
2. Calibration diagnostic bucket analysis (0.0-0.1, ..., 0.9-1.0).
3. Player-level & subgroup sanity checks (Nailed starter, Regular starter, Rotation-prone, Bench player, Low-minute player, Promoted player).
4. Representative error analysis on test set.
5. Production inference layer with automatic fallback to deterministic baseline.
6. Integration into ProjectionEngine replacing expected_minutes parameter cleanly (no double counting).
7. Versioning: production model expected_minutes_v1, baseline expected_minutes_baseline_v1.
8. API diagnostics endpoint updated to expose ML minutes, baseline minutes, P(start), P(60+), P(0).
9. Full pytest test suite passing (100%).
```
