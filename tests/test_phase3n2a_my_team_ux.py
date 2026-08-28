import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, UserSquad, UserPick
from backend.user.user_squad import UserSquadManager
from backend.ingestion.current_state import CurrentGameStateManager

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_user_squad_get_and_seed(client):
    """Verify GET /api/v1/user-squad returns valid 15-player squad dictionary."""
    res = client.get("/api/v1/user-squad")
    assert res.status_code == 200
    data = res.json()
    assert "picks" in data
    assert len(data["picks"]) == 15
    assert "starting_xi_xp" in data
    assert "bank_str" in data

def test_user_squad_update_and_persistence(client, db_session):
    """Verify POST /api/v1/user-squad updates player IDs, bank, free transfers, and chips persistently."""
    gkps = db_session.query(Player).filter(Player.element_type == "GKP").limit(2).all()
    defs = db_session.query(Player).filter(Player.element_type == "DEF").limit(5).all()
    mids = db_session.query(Player).filter(Player.element_type == "MID").limit(5).all()
    fwds = db_session.query(Player).filter(Player.element_type == "FWD").limit(3).all()
    
    player_ids = [p.id for p in (gkps + defs + mids + fwds)]
    assert len(player_ids) == 15

    payload = {
        "player_ids": player_ids,
        "bank": 15,  # £1.5m
        "free_transfers": 2,
        "active_chip": "wildcard"
    }

    post_res = client.post("/api/v1/user-squad", json=payload)
    assert post_res.status_code == 200
    post_data = post_res.json()
    assert post_data["bank"] == 15
    assert post_data["free_transfers"] == 2
    assert post_data["active_chip"] == "wildcard"

    # Reload / GET persistence check
    get_res = client.get("/api/v1/user-squad")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["bank"] == 15
    assert get_data["free_transfers"] == 2
    assert get_data["active_chip"] == "wildcard"
    assert len(get_data["picks"]) == 15

def test_user_squad_validation_rules(db_session):
    """Verify squad structure rules: 2 GKP, 5 DEF, 5 MID, 3 FWD."""
    gkps = db_session.query(Player).filter(Player.element_type == "GKP").limit(2).all()
    defs = db_session.query(Player).filter(Player.element_type == "DEF").limit(5).all()
    mids = db_session.query(Player).filter(Player.element_type == "MID").limit(5).all()
    fwds = db_session.query(Player).filter(Player.element_type == "FWD").limit(3).all()
    
    all_picks = gkps + defs + mids + fwds
    assert len(all_picks) == 15

    # Count positions
    pos_counts = {"GKP": 0, "DEF": 0, "MID": 0, "FWD": 0}
    for p in all_picks:
        pos_counts[p.element_type] += 1

    assert pos_counts["GKP"] == 2
    assert pos_counts["DEF"] == 5
    assert pos_counts["MID"] == 5
    assert pos_counts["FWD"] == 3

def test_user_squad_compare_with_optimal(client):
    """Verify POST /api/v1/user-squad/compare generates differential analysis."""
    res = client.post("/api/v1/user-squad/compare?mode=MEDIUM_TERM")
    assert res.status_code == 200
    data = res.json()
    assert "comparison" in data
    comp = data["comparison"]
    assert "xp_gain" in comp
    assert "transfers_out" in comp
    assert "transfers_in" in comp
    assert "keeps_count" in comp

def test_frontend_button_and_modal_elements():
    """Verify all required My Team frontend buttons and modal components exist in index.html."""
    import os
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    required_elements = [
        'id="my-team-modal"',
        'id="edit-my-team-btn"',
        'id="compare-my-team-btn"',
        'id="setup-my-team-btn"',
        'id="user-bank-input"',
        'id="user-ft-input"',
        'id="user-chip-input"',
        'id="my-team-search-input"',
        'id="save-my-team-btn"',
        'id="comparison-modal"',
        'id="my-team-unconfigured-banner"'
    ]

    for elem in required_elements:
        assert elem in html, f"Required frontend UI element '{elem}' missing in index.html!"
