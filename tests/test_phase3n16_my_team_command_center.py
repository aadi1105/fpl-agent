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

# ==================================================
# PHASE 3N.16 — MY TEAM COMMAND CENTER TESTS
# ==================================================

def get_valid_15_player_ids(db_session):
    gkps = [p.id for p in db_session.query(Player).filter(Player.element_type == "GKP").limit(2).all()]
    defs = [p.id for p in db_session.query(Player).filter(Player.element_type == "DEF").limit(5).all()]
    mids = [p.id for p in db_session.query(Player).filter(Player.element_type == "MID").limit(5).all()]
    fwds = [p.id for p in db_session.query(Player).filter(Player.element_type == "FWD").limit(3).all()]
    return gkps + defs + mids + fwds

def test_user_squad_edit_and_persistence(client, db_session):
    """Verify user squad can be updated via POST /api/v1/user-squad and persists upon reload."""
    valid_ids = get_valid_15_player_ids(db_session)
    assert len(valid_ids) == 15

    cap_id = valid_ids[0]
    vc_id = valid_ids[1]

    payload = {
        "player_ids": valid_ids,
        "bank": 5,
        "free_transfers": 2,
        "active_chip": "none",
        "captain_id": cap_id,
        "vice_captain_id": vc_id,
        "starter_ids": valid_ids[:11]
    }

    res = client.post("/api/v1/user-squad", json=payload)
    assert res.status_code == 200
    updated = res.json()

    assert updated["bank"] == 5
    assert updated["bank_str"] == "£0.5m"
    assert updated["free_transfers"] == 2

    # Verify persistence via GET
    get_res = client.get("/api/v1/user-squad")
    assert get_res.status_code == 200
    persisted = get_res.json()
    assert persisted["bank"] == 5
    assert persisted["free_transfers"] == 2

def test_user_squad_substitution(client, db_session):
    """Verify bench player can be swapped into starting XI legally."""
    valid_ids = get_valid_15_player_ids(db_session)
    starters = valid_ids[:11]
    bench = valid_ids[11:]

    # Setup initial squad
    payload = {
        "player_ids": valid_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": valid_ids[0],
        "vice_captain_id": valid_ids[1],
        "starter_ids": starters
    }
    client.post("/api/v1/user-squad", json=payload)

    # Swap starter 1 with bench 1 of same position
    starter_id = starters[-1]
    bench_id = bench[-1]

    new_starters = [id for id in starters if id != starter_id] + [bench_id]

    sub_payload = {
        "player_ids": valid_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": valid_ids[0],
        "vice_captain_id": valid_ids[1],
        "starter_ids": new_starters
    }

    res = client.post("/api/v1/user-squad", json=sub_payload)
    assert res.status_code == 200
    new_squad = res.json()

    new_picks = new_squad.get("picks", [])
    new_starter_ids = [p["id"] for p in new_picks if p.get("is_starter")]
    assert bench_id in new_starter_ids
    assert starter_id not in new_starter_ids

def test_edit_squad_button_and_modal_in_frontend(client):
    """Verify EDIT SQUAD button and editor modal elements exist in index.html."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "id=\"edit-my-team-btn\"" in html
    assert "EDIT SQUAD" in html
    assert "openEditSquadModal()" in html
    assert "saveUserSquad()" in html
    assert "id=\"my-team-modal\"" in html
    assert "id=\"user-bank-input\"" in html

def test_optimizer_uses_user_squad_in_comparison(client):
    """Verify /api/v1/user-squad/compare returns actionable transfer recommendation for user squad."""
    res = client.post("/api/v1/user-squad/compare?mode=CURRENT_GW_PLUS_3")
    assert res.status_code == 200
    data = res.json()
    assert "comparison" in data
    comp = data["comparison"]
    assert "my_squad_starting_xp" in comp
    assert "optimal_squad_starting_xp" in comp
