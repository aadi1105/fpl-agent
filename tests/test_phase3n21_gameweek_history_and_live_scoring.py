import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, UserSquad

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
# PHASE 3N.21 — GAMEWEEK HISTORY & LIVE FPL SCORING TESTS
# ==================================================

def test_gameweeks_endpoint_loads(client):
    """Verify GET /api/v1/gameweeks returns 38 gameweeks with active current GW detection."""
    res = client.get("/api/v1/gameweeks")
    assert res.status_code == 200
    gws = res.json()
    assert isinstance(gws, list)
    assert len(gws) == 38

    current = [g for g in gws if g["is_current"]]
    assert len(current) == 1
    assert current[0]["status"] in ["LIVE", "COMPLETED"]

def test_completed_gameweek_snapshot_returns_actual_points(client):
    """Verify GW1 snapshot returns actual points, scoreboard metrics, captain bonus, and chip info."""
    res = client.get("/api/v1/user-squad/gameweek/1")
    assert res.status_code == 200
    snap = res.json()

    assert snap["gw"] == 1
    assert snap["is_future"] is False
    assert snap["starting_xi_points"] is not None
    assert "captain_bonus" in snap
    assert "bench_points" in snap
    assert "active_chip" in snap
    assert "starting_11" in snap
    assert len(snap["starting_11"]) == 11

    # Check starter cards contain actual_pts and projected_xp
    for p in snap["starting_11"]:
        assert "actual_pts" in p
        assert "projected_xp" in p
        assert p["actual_pts"] is not None

def test_future_gameweek_snapshot_does_not_fabricate_points(client):
    """Verify future Gameweek (GW3) returns UPCOMING status and NO fabricated actual points."""
    res = client.get("/api/v1/user-squad/gameweek/3")
    assert res.status_code == 200
    snap = res.json()

    assert snap["gw"] == 3
    assert snap["status"] == "UPCOMING"
    assert snap["is_future"] is True
    assert snap["starting_xi_points"] is None
    assert "starting_xi_xp" in snap
    assert snap["starting_xi_xp"] > 0.0

    # Ensure actual_pts is None for every player in future GW
    for p in snap["starting_11"]:
        assert p["actual_pts"] is None
        assert p["projected_xp"] > 0.0

def test_historical_browsing_does_not_mutate_saved_squad(client, db_session):
    """Verify browsing historical GW snapshots DOES NOT alter or overwrite the saved editable user squad in DB."""
    # Ensure current saved squad state
    res_orig = client.get("/api/v1/user-squad")
    assert res_orig.status_code == 200
    orig_sq = res_orig.json()

    # Browse GW1, GW2, GW3
    client.get("/api/v1/user-squad/gameweek/1")
    client.get("/api/v1/user-squad/gameweek/3")

    # Fetch current saved squad again and verify identical state
    res_after = client.get("/api/v1/user-squad")
    assert res_after.status_code == 200
    after_sq = res_after.json()

    assert orig_sq["squad_id"] == after_sq["squad_id"]
    assert orig_sq["bank"] == after_sq["bank"]
    assert orig_sq["free_transfers"] == after_sq["free_transfers"]
    
    orig_pids = [p["id"] for p in orig_sq.get("picks", [])]
    after_pids = [p["id"] for p in after_sq.get("picks", [])]
    assert orig_pids == after_pids

def test_fpl_live_endpoint(client):
    """Verify GET /api/v1/fpl/live/1 returns live player points mapping."""
    res = client.get("/api/v1/fpl/live/1")
    assert res.status_code == 200
    live_map = res.json()
    assert isinstance(live_map, dict)
    assert len(live_map) > 0

    first_key = list(live_map.keys())[0]
    p = live_map[first_key]
    assert "total_points" in p
    assert "minutes" in p
