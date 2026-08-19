# Phase 3D: Production Model Validation, Retraining & Deployment

## Prompt Reference & Guidance

- **Primary Goal**: Perform comprehensive multi-season chronological walk-forward validation across historical FPL data, train and deploy versioned production v2 LightGBM model artifacts, update system inference wrappers, re-generate fresh 2026/27 player projections, run model-vs-consensus diagnostics, and verify optimizer behavior without altering optimizer code or objectives.
- **Strict Scope Restrictions**:
  1. Freeze production v1 baseline model artifacts in `models/` intact for complete baseline reproducibility.
  2. Perform chronological out-of-sample walk-forward evaluation across 3 multi-season folds.
  3. Deploy v2 artifacts (`expected_minutes_v2.pkl`, `xg_v2.pkl`, `xa_v2.pkl`) to `models/`.
  4. Perform target player diagnostic audits (Haaland, Bruno Fernandes, João Pedro, Calvert-Lewin, Awoniyi, Osula, Beto, Marmoush, Gabriel, Semenyo, Mbeumo, Saka).
  5. Perform Bruno Fernandes sanity diagnostic and assign structural classification.
  6. Execute optimizer gate across all 4 modes without tuning optimizer weights or constraints.
