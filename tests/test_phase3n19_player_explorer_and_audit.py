import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player

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
# PHASE 3N.19 — PLAYER DATA EXPLORER & MODEL AUDIT TESTS
# ==================================================

def test_player_explorer_endpoint_loads(client):
    """Verify player explorer endpoint returns 200 with populated player list."""
    res = client.get("/api/v1/players/explorer?limit=600")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0

    first = data[0]
    assert "id" in first
    assert "web_name" in first
    assert "position" in first
    assert "team_name" in first
    assert "price_str" in first
    assert "total_xp" in first
    assert "xMins" in first

def test_player_explorer_search_by_name_and_team(client):
    """Verify search by full name, partial name, and club."""
    res_bruno = client.get("/api/v1/players/explorer?query=Bruno")
    assert res_bruno.status_code == 200
    brunos = res_bruno.json()
    assert len(brunos) > 0
    assert any("Bruno" in p["web_name"] or "Bruno" in (p["first_name"] or "") for p in brunos)

    res_arsenal = client.get("/api/v1/players/explorer?query=ARS")
    assert res_arsenal.status_code == 200
    gunners = res_arsenal.json()
    assert len(gunners) > 0
    assert any(p["team_name"] == "ARS" for p in gunners)

def test_player_explorer_position_filter(client):
    """Verify position filtering for GKP, DEF, MID, FWD."""
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        res = client.get(f"/api/v1/players/explorer?position={pos}")
        assert res.status_code == 200
        data = res.json()
        assert len(data) > 0
        assert all(p["position"] == pos for p in data)

def test_current_gw_leaders_actual_points(client):
    """Verify current GW leaders endpoint returns players ranked exclusively by ACTUAL points (not xP)."""
    res5 = client.get("/api/v1/players/leaders?limit=5")
    assert res5.status_code == 200
    d5 = res5.json()
    assert d5["is_available"] is True
    assert len(d5["leaders"]) == 5

    res10 = client.get("/api/v1/players/leaders?limit=10")
    assert res10.status_code == 200
    d10 = res10.json()
    assert len(d10["leaders"]) == 10

    # Check ordering is monotonically non-increasing by actual points
    pts = [l["actual_gw_points"] for l in d10["leaders"]]
    assert pts == sorted(pts, reverse=True)

def test_player_detail_endpoint(client, db_session):
    """Verify player detail endpoint returns profile, upcoming fixtures, model metrics, and actual points."""
    player = db_session.query(Player).first()
    assert player is not None

    res = client.get(f"/api/v1/players/{player.id}/detail")
    assert res.status_code == 200
    detail = res.json()

    assert detail["id"] == player.id
    assert detail["web_name"] == player.web_name
    assert "position" in detail
    assert "team_name" in detail
    assert "price_str" in detail
    assert "upcoming_fixtures" in detail
    assert len(detail["upcoming_fixtures"]) > 0

    # Ensure upcoming fixtures do NOT contain GW0
    assert all(f["gw"] > 0 for f in detail["upcoming_fixtures"])

    assert "next_gw_xp" in detail
    assert "next_gw_xmins" in detail
    assert "expected_goals" in detail
    assert "expected_assists" in detail
    assert "historical_points" in detail

def test_model_audit_endpoint_no_nameerror(client):
    """Verify consensus audit endpoint succeeds (HTTP 200) without 500 NameError."""
    res = client.get("/api/v1/projections/consensus_audit?target_gw=2")
    assert res.status_code == 200
    audited = res.json()
    assert isinstance(audited, list)
    assert len(audited) > 0
    first = audited[0]
    assert "model_rank" in first
    assert "consensus_rank" in first
    assert "classification" in first

def test_frontend_explorer_and_audit_components(client):
    """Verify frontend HTML contains Player Explorer, GW Leaders, Model Audit, and detail modal handlers."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "PLAYER EXPLORER & RESEARCH TOOL" in html
    assert "CURRENT GAMEWEEK LEADERS" in html
    assert "EXPECTED MINUTES & ROLE COMPETITION AUDIT" in html
    assert "fetchExplorerPlayers" in html
    assert "fetchCurrentGwLeaders" in html
    assert "openPlayerDetailModal" in html
    assert "retry" in html.lower()
