import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, Team
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
# PHASE 3N.12 — EXPECTED MINUTES & FRESHNESS TESTS
# ==================================================

def test_gkp_competition_reconciliation(db_session):
    """Verify Goalkeeper role competition reconciliation scales backup GKPs to 0.0 xMins."""
    engine = ProjectionEngine(db_session)
    mci = db_session.query(Team).filter(Team.short_name == "MCI").first()
    assert mci is not None

    gkps = db_session.query(Player).filter(Player.team_id == mci.id, Player.element_type == "GKP").all()
    assert len(gkps) >= 2

    bd_list = [engine.calculate_player_xp_breakdown(g) for g in gkps]
    top_gkp_bd = max(bd_list, key=lambda b: b["xMins"])
    backup_gkp_bds = [b for b in bd_list if b["web_name"] != top_gkp_bd["web_name"]]

    # Starting GKP gets >=85 xMins, backups get 0 xMins
    assert top_gkp_bd["xMins"] >= 85.0
    for b in backup_gkp_bds:
        assert b["xMins"] == 0.0

def test_data_freshness_api_endpoint(client):
    """Verify /api/v1/state/status returns accurate snapshot generated_at timestamp and current GW."""
    res = client.get("/api/v1/state/status")
    assert res.status_code == 200
    data = res.json()
    assert data["current_gw"] in [1, 2]
    assert "snapshot_version" in data
    assert "generated_at" in data
    assert len(data["generated_at"]) > 0

def test_optimizer_consumes_reconciled_minutes(db_session):
    """Verify optimizer builds 15-player squad and starting 11 consuming reconciled minutes."""
    opt = SquadOptimizer(db_session)
    res = opt.solve_squad_selection(mode="CURRENT_GW_ONLY", current_gw=1)
    
    # Check that backup GKPs with 0 xMins are not chosen for starting 11
    starters = res["starting_11"]
    gkps = [p for p in starters if p["element_type"] == "GKP"]
    assert len(gkps) == 1
    assert gkps[0]["gw0_xp"] > 0.0
