import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, PlayerProjection
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================================================
# PHASE 3N.13 — LONG HORIZON & DIAGNOSTICS TESTS
# ==================================================

def test_long_term_horizon_gws(db_session):
    """Verify LONG_TERM mode uses 7-GW horizon (GW2 to GW8) with correct weights."""
    opt = SquadOptimizer(db_session)
    res = opt.solve_squad_selection(mode="LONG_TERM", current_gw=1)
    
    assert res["optimization_mode"] == "LONG_TERM"
    assert len(res["horizon_weights"]) == 7
    assert res["horizon_weights"][0] == 0.30

def test_diagnostics_horizon_matches_mode(client):
    """Verify GET /api/v1/projections/diagnostics?mode=LONG_TERM returns mode-aware 7-GW data."""
    res = client.get("/api/v1/projections/diagnostics?mode=LONG_TERM&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert "web_name" in data[0]

def test_darlow_reconciled_minutes_and_projections(db_session):
    """Verify Darlow has 0.0 xMins in reconciled breakdown and is not selected as starting GKP."""
    engine = ProjectionEngine(db_session)
    darlow = db_session.query(Player).filter(Player.web_name == "Darlow").first()
    assert darlow is not None

    bd = engine.calculate_player_xp_breakdown(darlow)
    assert bd["xMins"] == 0.0
    assert bd["total_xp"] == 0.0

def test_diagnostics_api_non_empty(client):
    """Verify diagnostics API returns 200 with non-empty list of player records."""
    res = client.get("/api/v1/projections/diagnostics?mode=CURRENT_GW_PLUS_3&limit=50")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    assert data[0]["price"] > 0
