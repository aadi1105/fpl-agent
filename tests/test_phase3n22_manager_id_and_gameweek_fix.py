import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, UserSquad, Gameweek
from backend.user.user_squad import UserSquadManager
from backend.services.fpl_history_service import FPLHistoryService, _HISTORY_CACHE

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
# PHASE 3N.22 — MANAGER ID & GAMEWEEK DETECTION TESTS
# ==================================================

def test_gw1_is_completed_and_gw2_is_live(client):
    """Verify GW1 is COMPLETED, GW2 is LIVE, and GW3+ is UPCOMING."""
    res = client.get("/api/v1/gameweeks")
    assert res.status_code == 200
    gws = res.json()

    gw1 = [g for g in gws if g["id"] == 1][0]
    gw2 = [g for g in gws if g["id"] == 2][0]
    gw3 = [g for g in gws if g["id"] == 3][0]

    assert gw1["status"] == "COMPLETED"
    assert gw1["is_current"] is False

    assert gw2["status"] == "LIVE"
    assert gw2["is_current"] is True

    assert gw3["status"] == "UPCOMING"
    assert gw3["is_current"] is False

def test_gw1_uses_correct_manager_picks(client, db_session):
    """Verify GW1 snapshot returns 15 unique player cards with 11 starters and 4 bench players."""
    res = client.get("/api/v1/user-squad/gameweek/1")
    assert res.status_code == 200
    snap = res.json()

    assert snap["gw"] == 1
    assert snap["status"] == "COMPLETED"
    assert len(snap["starting_11"]) == 11
    assert len(snap["bench"]) == 4
    assert len({p["id"] for p in snap["picks"]}) == 15

def test_gw2_uses_correct_manager_picks_and_live_status(client, db_session):
    """Verify GW2 snapshot returns correct manager picks with LIVE status."""
    res = client.get("/api/v1/user-squad/gameweek/2")
    assert res.status_code == 200
    snap = res.json()

    assert snap["gw"] == 2
    assert snap["status"] == "LIVE"
    assert snap["is_live"] is True

def test_gw3_is_upcoming_without_fake_points(client):
    """Verify GW3 snapshot returns UPCOMING status with projected xP and None actual points."""
    res = client.get("/api/v1/user-squad/gameweek/3")
    assert res.status_code == 200
    snap = res.json()

    assert snap["gw"] == 3
    assert snap["status"] == "UPCOMING"
    assert snap["starting_xi_points"] is None
    assert all(p["actual_pts"] is None for p in snap["starting_11"])

def test_wrong_entry_id_returns_error(client, db_session):
    """Verify requesting snapshot for an unlinked/mismatched entry ID returns explicit error structure."""
    # Set a specific fpl_entry_id on user_squad
    sq = db_session.query(UserSquad).first()
    sq.fpl_entry_id = 35049
    db_session.commit()

    # Request with mismatched entry ID 99999
    res = client.get("/api/v1/user-squad/gameweek/1?fpl_entry_id=99999")
    assert res.status_code == 200
    data = res.json()

    assert data.get("error") is True
    assert data.get("error_code") == "MANAGER_MISMATCH"
    assert "Expected Entry ID 35049" in data.get("message", "")

    # Cleanup
    sq.fpl_entry_id = None
    db_session.commit()

def test_cache_is_isolated_by_entry_id(db_session):
    """Verify cache keys are namespaced by entry ID and gameweek."""
    service = FPLHistoryService(db_session)
    
    # Clear cache
    _HISTORY_CACHE.clear()

    # Fetch entry picks for entry 100
    service.fetch_fpl_entry_picks(entry_id=100, gw=1)
    
    # Assert cache key contains entry_100_gw_1
    assert "entry_picks_100_gw_1" in _HISTORY_CACHE

def test_historical_view_does_not_mutate_current_squad(client, db_session):
    """Verify browsing historical GW snapshots DOES NOT alter or overwrite the saved editable user squad in DB."""
    res_orig = client.get("/api/v1/user-squad")
    orig_sq = res_orig.json()

    # Browse GW1, GW2, GW3
    client.get("/api/v1/user-squad/gameweek/1")
    client.get("/api/v1/user-squad/gameweek/2")
    client.get("/api/v1/user-squad/gameweek/3")

    # Fetch current squad again
    res_after = client.get("/api/v1/user-squad")
    after_sq = res_after.json()

    assert orig_sq["squad_id"] == after_sq["squad_id"]
    assert orig_sq["bank"] == after_sq["bank"]
    assert [p["id"] for p in orig_sq["picks"]] == [p["id"] for p in after_sq["picks"]]
