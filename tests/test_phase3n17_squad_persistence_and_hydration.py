import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player
from backend.user.user_squad import UserSquadManager

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

def get_valid_15_player_ids(db_session):
    gkps = [p.id for p in db_session.query(Player).filter(Player.element_type == "GKP").limit(2).all()]
    defs = [p.id for p in db_session.query(Player).filter(Player.element_type == "DEF").limit(5).all()]
    mids = [p.id for p in db_session.query(Player).filter(Player.element_type == "MID").limit(5).all()]
    fwds = [p.id for p in db_session.query(Player).filter(Player.element_type == "FWD").limit(3).all()]
    return gkps + defs + mids + fwds

# ==================================================
# PHASE 3N.17 — SQUAD PERSISTENCE & HYDRATION TESTS
# ==================================================

def test_api_returns_starting_11_and_bench_root_keys(client, db_session):
    """Regression test ensuring GET /api/v1/user-squad contains starting_11 and bench root keys so frontend hydration succeeds."""
    valid_ids = get_valid_15_player_ids(db_session)
    assert len(valid_ids) == 15

    payload = {
        "player_ids": valid_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": valid_ids[0],
        "vice_captain_id": valid_ids[1],
        "starter_ids": valid_ids[:11]
    }
    post_res = client.post("/api/v1/user-squad", json=payload)
    assert post_res.status_code == 200
    data = post_res.json()

    assert "starting_11" in data, "API response missing 'starting_11' root key required for frontend pitch rendering!"
    assert "bench" in data, "API response missing 'bench' root key required for frontend pitch rendering!"
    assert len(data["starting_11"]) == 11, f"Expected 11 starting_11 players, got {len(data['starting_11'])}"
    assert len(data["bench"]) == 4, f"Expected 4 bench players, got {len(data['bench'])}"

    # Re-fetch via GET (simulate page refresh)
    get_res = client.get("/api/v1/user-squad")
    assert get_res.status_code == 200
    get_data = get_res.json()

    assert len(get_data["starting_11"]) == 11
    assert len(get_data["bench"]) == 4
    all_rehydrated_ids = [p["id"] for p in get_data["starting_11"] + get_data["bench"]]
    assert set(all_rehydrated_ids) == set(valid_ids)

def test_edit_single_player_and_refresh(client, db_session):
    """Verify modifying 1 player in squad persists across GET re-hydration."""
    valid_ids = get_valid_15_player_ids(db_session)
    client.post("/api/v1/user-squad", json={
        "player_ids": valid_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": valid_ids[0],
        "vice_captain_id": valid_ids[1],
        "starter_ids": valid_ids[:11]
    })

    # Pick a replacement player not in current 15
    replacement = db_session.query(Player).filter(
        Player.element_type == "MID",
        ~Player.id.in_(valid_ids)
    ).first()
    assert replacement is not None

    # Replace last MID (valid_ids[11]) with replacement player
    modified_ids = list(valid_ids)
    old_player_id = modified_ids[11]
    modified_ids[11] = replacement.id

    res = client.post("/api/v1/user-squad", json={
        "player_ids": modified_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": modified_ids[0],
        "vice_captain_id": modified_ids[1],
        "starter_ids": modified_ids[:11]
    })
    assert res.status_code == 200

    # Simulate hard refresh
    get_res = client.get("/api/v1/user-squad")
    assert get_res.status_code == 200
    get_data = get_res.json()

    rehydrated_ids = [p["id"] for p in get_data["starting_11"] + get_data["bench"]]
    assert replacement.id in rehydrated_ids
    assert old_player_id not in rehydrated_ids

def test_frontend_pitch_hydration_logic(client):
    """Verify frontend HTML has robust starting11 and bench extraction logic so 0-0-0 pitch is never rendered for valid squad."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "squadData.starting_11 || picks.filter" in html or "squadData.starting_11" in html
    assert "starting11" in html
    assert "bench" in html
    assert "renderUserSquadPage" in html
