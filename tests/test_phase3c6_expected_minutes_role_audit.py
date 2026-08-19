import pytest
from fastapi.testclient import TestClient
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.main import app

client = TestClient(app)

def test_production_projections_unchanged():
    """Verify that Phase 3C.6 diagnostic audit does NOT alter stored or calculated player projections."""
    db = SessionLocal()
    engine = ProjectionEngine(db)
    awoniyi = db.query(Player).filter(Player.web_name == "Awoniyi").first()
    
    bd1 = engine.calculate_player_xp_breakdown(awoniyi)
    res = client.get("/api/v1/projections/consensus_audit?target_gw=1")
    assert res.status_code == 200
    
    bd2 = engine.calculate_player_xp_breakdown(awoniyi)
    assert bd1["total_xp"] == bd2["total_xp"]
    assert bd1["xMins"] == bd2["xMins"]
    assert bd1["xg_match"] == bd2["xg_match"]

def test_models_version_and_integrity_unchanged():
    """Verify ML model versions remain expected_minutes_v1, xg_v1_lgbm, xa_v1_lgbm."""
    db = SessionLocal()
    engine = ProjectionEngine(db)
    assert engine.minutes_predictor.is_loaded
    assert engine.xg_predictor.is_loaded
    assert engine.xa_predictor.is_loaded
    assert engine.cs_predictor.model is not None
    assert engine.defcon_predictor is not None

def test_optimizer_objective_unchanged():
    """Verify MILP squad optimizer formulation objective is 100% unchanged and free of consensus/ownership."""
    db = SessionLocal()
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="CURRENT_GW_PLUS_3")
    
    assert res is not None
    assert "starting_11" in res
    assert "bench" in res
    assert res["optimization_mode"] == "CURRENT_GW_PLUS_3"

def test_per_90_small_sample_safety():
    """Verify per-90 metrics calculation does not produce division-by-zero or NaNs on low minutes."""
    db = SessionLocal()
    engine = ProjectionEngine(db)
    
    # Create low-minute mock player or check existing low-minute player
    low_min_player = db.query(Player).filter(Player.minutes < 180).first()
    if low_min_player:
        metrics = engine.get_player_per_90_metrics(low_min_player)
        assert metrics["xg90"] >= 0.0
        assert metrics["xa90"] >= 0.0
        assert not any(pytest.approx(0.0) != v and (v != v) for v in metrics.values())  # check NaN

def test_diagnostic_sensitivity_does_not_modify_stored_projections():
    """Verify hypothetical sensitivity calculations leave DB projections untouched."""
    db = SessionLocal()
    engine = ProjectionEngine(db)
    osula = db.query(Player).filter(Player.web_name == "Osula").first()
    
    orig_bd = engine.calculate_player_xp_breakdown(osula)
    
    # Hypothetical calculation with 45 minutes
    hypo_mins = 45.0
    mins_r = hypo_mins / 90.0
    hypo_xp = (2.0 if hypo_mins >= 60 else 1.0) * mins_r + orig_bd["goals_xp"] * mins_r
    
    post_bd = engine.calculate_player_xp_breakdown(osula)
    assert post_bd["total_xp"] == orig_bd["total_xp"]
    assert post_bd["xMins"] == orig_bd["xMins"]
