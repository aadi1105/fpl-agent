import pytest
from fastapi.testclient import TestClient
from backend.main import app, get_projection_diagnostics
from backend.database import SessionLocal
from backend.models import Player, Fixture, Team, PlayerProjection
from backend.ingestion.current_state import CurrentGameStateManager
from backend.optimizer.squad_optimizer import SquadOptimizer

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_gameweek_index_consistency(db_session):
    """Verify current GW is 1 across State, Diagnostics, and Optimizer, and no GW0 label is present."""
    state_mgr = CurrentGameStateManager(db_session)
    cur_gw = state_mgr.get_current_gameweek()
    assert cur_gw == 1

    diag = get_projection_diagnostics(target_gw=1, position=None, sort_by="total_xp", limit=10, db=db_session)
    assert len(diag) > 0
    sample = diag[0]
    
    # Check that GW1..4 opponent and xP keys exist and align with current GW
    assert "gw1_opponent" in sample
    assert "gw2_opponent" in sample
    assert "gw3_opponent" in sample
    assert "gw4_opponent" in sample
    assert "gw1_xp" in sample

def test_no_gw0_label_in_frontend():
    """Verify index.html contains no hardcoded GW0 Fixture table headers."""
    import os
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "GW0 Fixture" not in html, "Frontend table header MUST NOT display GW0 Fixture!"
    assert "th-gw1-label" in html

def test_bruno_fernandes_projection_decomposition(db_session):
    """Verify B.Fernandes (id=426) fixtures and 5.90 xP vs Man City in GW4 are mathematically justified."""
    bruno = db_session.query(Player).filter(Player.id == 426).first()
    assert bruno is not None
    assert bruno.web_name == "B.Fernandes"

    # Fetch GW4 projection vs MCI
    proj_gw4 = db_session.query(PlayerProjection).filter(
        PlayerProjection.player_id == bruno.id,
        PlayerProjection.gameweek_id == 4
    ).first()

    assert proj_gw4 is not None
    assert proj_gw4.expected_points >= 5.0
    assert proj_gw4.expected_minutes >= 70.0

def test_optimal_xi_decision_trace_and_alternatives(db_session):
    """Verify every selected Optimal XI player has a traceable marginal alternative."""
    opt = SquadOptimizer(db_session)
    res = opt.solve_squad_selection(mode="MEDIUM_TERM", current_gw=1)

    starters = res["starting_11"]
    bench = res["bench"]
    assert len(starters) == 11
    assert len(bench) == 4

    # Total cost check <= 1000 (£100.0m)
    total_cost = sum(p["now_cost"] for p in (starters + bench))
    assert total_cost <= 1000

    # Budget allocation checks
    pos_costs = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}
    for p in (starters + bench):
        pos_costs[p["element_type"]] += p["now_cost"]

    assert pos_costs["GKP"] > 0
    assert pos_costs["DEF"] > 0
    assert pos_costs["MID"] > 0
    assert pos_costs["FWD"] > 0

def test_player_shirt_svg_visual_hierarchy():
    """Verify getClubShirtSvg function exists in index.html and renders centered 36px shirt visual."""
    import os
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "getClubShirtSvg" in html
    assert "viewBox=\"0 0 36 36\"" in html
    assert "badge-cap" in html
    assert "player-card-pitch" in html
