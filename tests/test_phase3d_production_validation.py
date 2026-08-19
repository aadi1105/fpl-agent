import os
import sys
import json
import pytest

sys.path.append(os.getcwd())
from backend.ml.minutes_predictor import MinutesPredictor
from backend.ml.xg_predictor import XGPredictor
from backend.ml.xa_predictor import XAPredictor
from backend.database import get_db
from backend.optimizer.squad_optimizer import SquadOptimizer

def test_baseline_v1_preservation():
    """Verify production v1 baseline artifacts exist and are preserved in models/."""
    v1_artifacts = [
        "minutes_start_v1.pkl",
        "minutes_regression_v1.pkl",
        "minutes_60plus_v1.pkl",
        "minutes_zero_v1.pkl",
        "xg_v1_lgbm.pkl",
        "xa_v1_lgbm.pkl"
    ]
    for filename in v1_artifacts:
        path = os.path.join("models", filename)
        assert os.path.exists(path), f"Baseline artifact {filename} missing!"
        assert os.path.getsize(path) > 100, f"Baseline artifact {filename} is corrupted or empty!"

def test_production_v2_artifacts():
    """Verify production v2 artifacts exist in models/."""
    v2_artifacts = [
        "expected_minutes_v2.pkl",
        "xg_v2.pkl",
        "xa_v2.pkl"
    ]
    for filename in v2_artifacts:
        path = os.path.join("models", filename)
        assert os.path.exists(path), f"Production v2 artifact {filename} missing!"
        assert os.path.getsize(path) > 50, f"Production v2 artifact {filename} is corrupted or empty!"

def test_walk_forward_metrics_improvement():
    """Verify walk-forward validation out-of-sample improvements recorded in scratch/phase3d_validation_results.json."""
    val_path = os.path.join("scratch", "phase3d_validation_results.json")
    assert os.path.exists(val_path), "Walk-forward validation results missing!"
    
    with open(val_path, "r") as f:
        data = json.load(f)
        
    assert "folds" in data, "Folds missing from validation results!"
    assert len(data["folds"]) == 3, "Expected 3 walk-forward validation folds!"
    
    # Assert fold 3 (2025/26 test set) demonstrated out-of-sample MAE improvement
    f3 = data["folds"][2]
    assert f3["imp_mins"] > 10.0, "Fold 3 minutes MAE improvement < 10%"
    assert f3["imp_brier"] > 20.0, "Fold 3 p_start Brier improvement < 20%"
    assert f3["imp_xg"] > 10.0, "Fold 3 xG deviance improvement < 10%"

def test_predictor_loading_v2():
    """Verify inference wrappers load production v2 models by default."""
    m_pred = MinutesPredictor()
    xg_pred = XGPredictor()
    xa_pred = XAPredictor()
    
    assert m_pred.is_loaded is True
    assert getattr(m_pred, "model_version", "") == "expected_minutes_v2"
    
    assert xg_pred.is_loaded is True
    assert getattr(xg_pred, "model_version", "") == "xg_v2"
    
    assert xa_pred.is_loaded is True
    assert getattr(xa_pred, "model_version", "") == "xa_v2"

def test_optimizer_gate_v2():
    """Verify optimizer runs cleanly on deployed v2 projections across all 4 modes."""
    db = next(get_db())
    opt = SquadOptimizer(db=db)
    
    for mode in ["CURRENT_GW_PLUS_3", "STRONG_XI_DUMP_BENCH", "BALANCED_BENCH", "MAXIMUM_SQUAD"]:
        res = opt.solve_squad_selection(mode=mode)
        assert res["squad_count"] == 15, f"Mode {mode} failed to select 15-man squad!"
        assert res["total_cost"] <= 1000, f"Mode {mode} violated £100.0m budget constraint!"
        assert len(res["starting_11"]) == 11, f"Mode {mode} failed to select 11 starters!"
        assert len(res["bench"]) == 4, f"Mode {mode} failed to select 4 bench players!"
        assert res["weighted_horizon_xp"] > 50.0, f"Mode {mode} produced invalid weighted xP!"
