import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, engine
from backend.models import Player, UserSquad, UserPick
from backend.user.user_squad import UserSquadManager
from backend.ingestion.current_state import CurrentGameStateManager

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

# ==================================================
# PART 1 — PRODUCTION DB SAFETY GUARD TEST
# ==================================================

def test_tests_cannot_mutate_production_db():
    """Verify test suite environment runs EXCLUSIVELY against fpl_test.db and NEVER production fpl.db."""
    db_url = os.environ.get("DATABASE_URL", "")
    assert "fpl_engine_test.db" in db_url or ":memory:" in db_url, f"TEST SAFETY VIOLATION! Tests must NOT touch fpl_engine.db! URL={db_url}"

# ==================================================
# PART 2 — NO ARSENAL FALLBACK & UNCONFIGURED STATE TESTS
# ==================================================

def test_no_saved_squad_produces_empty_setup_state(client, db_session):
    """Verify an unconfigured squad returns is_configured=False, picks=[], bank=0, FT=1, active_chip=None."""
    db_session.query(UserPick).delete()
    db_session.query(UserSquad).delete()
    db_session.commit()

    res = client.get("/api/v1/user-squad")
    assert res.status_code == 200
    data = res.json()

    assert data["is_configured"] is False
    assert len(data["picks"]) == 0, "Unconfigured squad MUST NOT contain any players!"
    assert data["bank"] == 0
    assert data["bank_str"] == "£0.0m"
    assert data["free_transfers"] == 1
    assert data["active_chip"] is None

def test_no_arsenal_fallback_when_unconfigured(db_session):
    """Verify missing user squad DOES NOT silently populate Arsenal squad."""
    db_session.query(UserPick).delete()
    db_session.query(UserSquad).delete()
    db_session.commit()

    mgr = UserSquadManager(db_session)
    squad_dict = mgr.get_user_squad_dict()

    assert squad_dict["is_configured"] is False
    assert len(squad_dict["picks"]) == 0
    assert not any(p["team_name"] == "ARS" for p in squad_dict["picks"])

# ==================================================
# PART 3 — PERSISTENCE & RELOAD INTEGRITY TESTS
# ==================================================

def test_save_and_reload_exact_15_players(client, db_session):
    """Verify saving a non-Arsenal squad persists exact 15 player IDs across reloads."""
    # Pick 15 players avoiding Arsenal (team_id != 1)
    all_players = db_session.query(Player).filter(Player.team_id != 1).limit(150).all()
    gkps = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    saved_ids = gkps + defs + mids + fwds
    assert len(saved_ids) == 15

    payload = {
        "player_ids": saved_ids,
        "bank": 0,  # £0.0m
        "free_transfers": 1,
        "active_chip": None
    }

    # Save
    post_res = client.post("/api/v1/user-squad", json=payload)
    assert post_res.status_code == 200

    # Reload / GET
    get_res = client.get("/api/v1/user-squad")
    assert get_res.status_code == 200
    get_data = get_res.json()

    assert get_data["is_configured"] is True
    assert len(get_data["picks"]) == 15
    restored_ids = [p["id"] for p in get_data["picks"]]
    assert set(restored_ids) == set(saved_ids), "Restored player IDs MUST match saved player IDs exactly!"

def test_bank_ft_chip_persist_together(client, db_session):
    """Verify player IDs, bank, free transfers, and active chip persist as ONE coherent state."""
    all_players = db_session.query(Player).limit(100).all()
    gkps = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    saved_ids = gkps + defs + mids + fwds

    payload = {
        "player_ids": saved_ids,
        "bank": 5,  # £0.5m
        "free_transfers": 1,
        "active_chip": "bboost"
    }

    client.post("/api/v1/user-squad", json=payload)

    get_data = client.get("/api/v1/user-squad").json()
    assert get_data["bank"] == 5
    assert get_data["bank_str"] == "£0.5m"
    assert get_data["free_transfers"] == 1
    assert get_data["active_chip"] == "bboost"

# ==================================================
# PART 4 — ISOLATION & NO-OVERWRITE TESTS
# ==================================================

def test_player_database_loading_cannot_overwrite_my_team(client):
    """Verify calling GET /api/v1/players DOES NOT mutate or overwrite user squad."""
    before_squad = client.get("/api/v1/user-squad").json()
    
    # Load player database
    client.get("/api/v1/players?limit=600&target_gw=1")
    
    after_squad = client.get("/api/v1/user-squad").json()
    assert before_squad["picks"] == after_squad["picks"]
    assert before_squad["bank"] == after_squad["bank"]

def test_optimizer_loading_cannot_overwrite_my_team(client):
    """Verify launching optimizer job DOES NOT mutate or overwrite user squad."""
    before_squad = client.get("/api/v1/user-squad").json()
    
    # Start optimization job
    payload = {"mode": "MEDIUM_TERM", "current_gw": 1, "total_budget": 1000, "max_players_per_team": 3}
    client.post("/api/v1/optimize/job", json=payload)
    
    after_squad = client.get("/api/v1/user-squad").json()
    assert before_squad["picks"] == after_squad["picks"]
    assert before_squad["bank"] == after_squad["bank"]
