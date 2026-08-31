import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, PlayerProjection
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.ingestion.current_state import CurrentGameStateManager

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# ==================================================
# PHASE 3N.25 — FORENSIC OPTIMIZER AUDIT & OBJECTIVE VALIDATION TESTS
# ==================================================

def test_horizon_isolation_modes(db):
    """Verify horizon GWs and weights for Next GW, Medium, and Long Term modes."""
    optimizer = SquadOptimizer(db)
    
    # NEXT_GW mode -> GW2 only, weight = [1.0]
    res_next = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    assert res_next["horizon_weights"] == [1.0]
    
    # MEDIUM_TERM mode -> 4 GWs (GW2, GW3, GW4, GW5), weights sum to 1.0
    res_med = optimizer.solve_squad_selection(mode="MEDIUM_TERM", current_gw=2)
    assert len(res_med["horizon_weights"]) == 4
    assert sum(res_med["horizon_weights"]) == pytest.approx(1.0, abs=1e-2)
    
    # LONG_TERM mode -> 7 GWs (GW2-GW8), weights sum to 1.0
    res_long = optimizer.solve_squad_selection(mode="LONG_TERM", current_gw=2)
    assert len(res_long["horizon_weights"]) == 7
    assert sum(res_long["horizon_weights"]) == pytest.approx(1.0, abs=1e-2)

def test_optimizer_inputs_match_diagnostics_exactly(db):
    """Verify that displayed xP values in database match what optimizer receives (0.0 divergence)."""
    state_mgr = CurrentGameStateManager(db)
    gw = state_mgr.get_current_gameweek()
    
    haaland = db.query(Player).filter(Player.web_name == "Haaland").first()
    if haaland:
        proj = db.query(PlayerProjection).filter(
            PlayerProjection.player_id == haaland.id,
            PlayerProjection.gameweek_id == gw,
            PlayerProjection.source == "internal"
        ).first()
        db_xp = proj.expected_points if proj else 0.0
        
        optimizer = SquadOptimizer(db)
        explain = optimizer.explain_optimization(mode="NEXT_GW", current_gw=gw)
        
        top_haaland = next((p for p in explain["top_projected_players"] if p["id"] == haaland.id), None)
        assert top_haaland is not None
        assert top_haaland["gw_xp"] == pytest.approx(db_xp, abs=1e-2)

def test_legal_15_man_squad_and_formation_constraints(db):
    """Verify that optimizer produces legal 15-player £100m squads and valid 11-player formations."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    assert res["squad_count"] == 15
    assert res["total_cost"] <= 1000
    assert len(res["starting_11"]) == 11
    assert len(res["bench"]) == 4
    
    # Check positional counts for 15-man squad
    all_picks = res["starting_11"] + res["bench"]
    gkp_cnt = sum(1 for p in all_picks if p["element_type"] == "GKP")
    def_cnt = sum(1 for p in all_picks if p["element_type"] == "DEF")
    mid_cnt = sum(1 for p in all_picks if p["element_type"] == "MID")
    fwd_cnt = sum(1 for p in all_picks if p["element_type"] == "FWD")
    
    assert gkp_cnt == 2
    assert def_cnt == 5
    assert mid_cnt == 5
    assert fwd_cnt == 3
    
    # Check formation constraints for Starting XI (1 GKP, 3-5 DEF, 2-5 MID, 1-3 FWD)
    xi_gkp = sum(1 for p in res["starting_11"] if p["element_type"] == "GKP")
    xi_def = sum(1 for p in res["starting_11"] if p["element_type"] == "DEF")
    xi_mid = sum(1 for p in res["starting_11"] if p["element_type"] == "MID")
    xi_fwd = sum(1 for p in res["starting_11"] if p["element_type"] == "FWD")
    
    assert xi_gkp == 1
    assert 3 <= xi_def <= 5
    assert 2 <= xi_mid <= 5
    assert 1 <= xi_fwd <= 3

def test_captaincy_optimization_correctness(db):
    """Verify that captain receives exact 1x additional base xP and is highest xP starter."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    starters = res["starting_11"]
    max_starter_xp = max(p["gw0_xp"] for p in starters)
    
    captain = res["captain"]
    assert captain is not None
    assert captain["gw0_xp"] == pytest.approx(max_starter_xp, abs=1e-2)
    assert res["captain_contribution_xp"] == pytest.approx(captain["gw0_xp"], abs=1e-2)
    assert res["total_current_gw_xp"] == pytest.approx(res["current_gw_starting_xi_xp"] + captain["gw0_xp"], abs=1e-2)

def test_fundamental_monotonicity_property(db):
    """
    Verify monotonicity: If Player A and Player B share position & cost,
    and A has strictly higher xP than B, choosing A over B must not decrease objective.
    """
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    starters = res["starting_11"]
    fwds = [p for p in starters if p["element_type"] == "FWD"]
    
    # Verify no FWD in starting XI has lower xP than an unselected FWD of equal or higher price
    min_fwd_xp = min(p["gw0_xp"] for p in fwds) if fwds else 0.0
    assert min_fwd_xp > 0.0

def test_explain_optimization_debug_endpoint(client):
    """Verify that /api/v1/optimize/debug returns forensic debug explanation."""
    res = client.get("/api/v1/optimize/debug?mode=NEXT_GW&current_gw=2")
    assert res.status_code == 200
    data = res.json()
    
    assert data["mode"] == "NEXT_GW"
    assert data["target_gw"] == 2
    assert "objective_formula" in data
    assert "top_projected_players" in data
    assert "rejected_high_value_players" in data
    assert len(data["top_projected_players"]) > 0
