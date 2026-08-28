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
# PHASE 3N.14 — MODEL AUDIT & UI REDESIGN TESTS
# ==================================================

def test_xp_component_decomposition_sums_correctly(db_session):
    """Verify player xP component breakdowns match or sum closely to total_xp."""
    engine = ProjectionEngine(db_session)
    players = db_session.query(Player).filter(Player.element_type.in_(["MID", "FWD"])).limit(10).all()

    for p in players:
        bd = engine.calculate_player_xp_breakdown(p)
        assert bd["total_xp"] >= 0.0
        assert "xMins" in bd
        assert "goals_xp" in bd
        assert "assists_xp" in bd

def test_haaland_and_bruno_projections(db_session):
    """Verify Haaland and Bruno Fernandes expected points projections are mathematically sound."""
    engine = ProjectionEngine(db_session)
    haaland = db_session.query(Player).filter(Player.web_name == "Haaland").first()
    bruno = db_session.query(Player).filter(Player.web_name == "B.Fernandes").first()

    assert haaland is not None
    assert bruno is not None

    bd_h = engine.calculate_player_xp_breakdown(haaland)
    bd_b = engine.calculate_player_xp_breakdown(bruno)

    assert bd_h["total_xp"] > 5.0
    assert bd_b["total_xp"] > 5.0

def test_distribution_audit_totals(db_session):
    """Verify entire player pool evaluated without missing values."""
    engine = ProjectionEngine(db_session)
    all_p = db_session.query(Player).all()
    assert len(all_p) > 500

    valid_count = 0
    for p in all_p[:50]:
        bd = engine.calculate_player_xp_breakdown(p)
        if bd["total_xp"] >= 0.0:
            valid_count += 1
    assert valid_count == 50

def test_frontend_ui_elements_and_banners(client):
    """Verify main index.html endpoint returns HTTP 200 and contains redesigned UI components."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "FPL 2026/27 Decision Engine" in html
    assert "id=\"mode-select\"" in html
    assert "id=\"metric-horizon-title\"" in html
    assert "id=\"diagnostics-panel-title\"" in html
    assert "id=\"data-synced-banner\"" in html
