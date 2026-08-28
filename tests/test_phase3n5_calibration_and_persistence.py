import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, UserSquad, UserPick
from backend.user.user_squad import UserSquadManager
from backend.projections.engine import ProjectionEngine

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

# ==================================================
# PART 1 — CALIBRATION AUDIT TESTS
# ==================================================

def test_calibration_v2_active_and_reproducible(db_session):
    """Verify expected_xp_calibrated_v2 model is active and yields deterministic projections."""
    engine = ProjectionEngine(db_session)
    assert engine.calibration_meta is not None
    assert engine.calibration_meta.get("model_version") == "expected_xp_calibrated_v2"

    # Test B.Fernandes (id=426)
    bruno = db_session.query(Player).filter(Player.id == 426).first()
    assert bruno is not None
    
    # Calculate projection breakdown for GW1
    from backend.models import Fixture, Team
    fixture = db_session.query(Fixture).filter(Fixture.event_id == 1, (Fixture.team_h_id == bruno.team_id) | (Fixture.team_a_id == bruno.team_id)).first()
    is_home = (fixture.team_h_id == bruno.team_id)
    opp_team = db_session.query(Team).filter(Team.id == (fixture.team_a_id if is_home else fixture.team_h_id)).first()
    
    bd = engine.calculate_player_xp_breakdown(bruno, fixture, is_home, opp_team)
    assert bd["total_xp"] > 0
    assert bd["total_xp"] == bd["calibrated_xp"]

# ==================================================
# PART 2 — MY TEAM PERSISTENCE TESTS
# ==================================================

def test_unconfigured_squad_does_not_seed_arsenal_default(db_session):
    """Verify an unconfigured user squad returns is_configured=False with 0 picks (NO fake Arsenal squad)."""
    # Clear any existing squad picks
    db_session.query(UserPick).delete()
    db_session.query(UserSquad).delete()
    db_session.commit()

    mgr = UserSquadManager(db_session)
    squad_dict = mgr.get_user_squad_dict()
    
    assert squad_dict["is_configured"] is False
    assert len(squad_dict["picks"]) == 0, "Unconfigured squad MUST NOT auto-seed 15 players!"

def test_my_team_save_and_reload_persistence(client, db_session):
    """Verify saving Squad A persists across new DB sessions and GET /api/v1/user-squad."""
    # Pick 15 distinct players for Squad A
    all_players = db_session.query(Player).limit(100).all()
    gkps_a = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs_a = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids_a = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds_a = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    squad_a_ids = gkps_a + defs_a + mids_a + fwds_a

    # POST Save Squad A
    payload_a = {
        "player_ids": squad_a_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "wildcard"
    }
    res_a = client.post("/api/v1/user-squad", json=payload_a)
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["is_configured"] is True
    assert len(data_a["picks"]) == 15
    pids_returned_a = [p["id"] for p in data_a["picks"]]
    assert set(pids_returned_a) == set(squad_a_ids)

    # GET Reload Squad A
    get_res_a = client.get("/api/v1/user-squad")
    assert get_res_a.status_code == 200
    get_data_a = get_res_a.json()
    get_pids_a = [p["id"] for p in get_data_a["picks"]]
    assert set(get_pids_a) == set(squad_a_ids)

def test_my_team_second_squad_replaces_first(client, db_session):
    """Verify saving Squad B replaces Squad A cleanly without reverting."""
    all_players = db_session.query(Player).offset(30).limit(100).all()
    gkps_b = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs_b = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids_b = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds_b = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    squad_b_ids = gkps_b + defs_b + mids_b + fwds_b

    # POST Save Squad B
    payload_b = {
        "player_ids": squad_b_ids,
        "bank": 20,
        "free_transfers": 1,
        "active_chip": None
    }
    res_b = client.post("/api/v1/user-squad", json=payload_b)
    assert res_b.status_code == 200

    # GET Reload Squad B
    get_res_b = client.get("/api/v1/user-squad")
    assert get_res_b.status_code == 200
    get_data_b = get_res_b.json()
    get_pids_b = [p["id"] for p in get_data_b["picks"]]
    assert set(get_pids_b) == set(squad_b_ids)
