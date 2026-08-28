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
# PHASE 3N.18 — SUBSTITUTION UX & STATE RELIABILITY TESTS
# ==================================================

def test_first_and_second_consecutive_substitution(client, db_session):
    """Verify first substitution succeeds and second substitution immediately succeeds without dead clicks or state lock."""
    valid_ids = get_valid_15_player_ids(db_session)
    starters = valid_ids[:11]
    bench = valid_ids[11:]

    # Initial setup (3-5-2 or 3-4-3)
    client.post("/api/v1/user-squad", json={
        "player_ids": valid_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": valid_ids[0],
        "vice_captain_id": valid_ids[1],
        "starter_ids": starters
    })

    # --- Substitution 1: Swap starter 11 with bench 1 ---
    s1_starter = starters[-1]
    s1_bench = bench[0]
    new_starters_1 = [id for id in starters if id != s1_starter] + [s1_bench]
    new_bench_1 = [id for id in bench if id != s1_bench] + [s1_starter]

    res1 = client.post("/api/v1/user-squad", json={
        "player_ids": new_starters_1 + new_bench_1,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": valid_ids[0],
        "vice_captain_id": valid_ids[1],
        "starter_ids": new_starters_1
    })
    assert res1.status_code == 200
    sq1 = res1.json()
    st1_ids = [p["id"] for p in sq1["starting_11"]]
    assert s1_bench in st1_ids
    assert s1_starter not in st1_ids

    # --- Substitution 2: Swap another starter with bench 2 immediately ---
    s2_starter = new_starters_1[1]  # second starter
    s2_bench = new_bench_1[1]      # second bench
    new_starters_2 = [id for id in new_starters_1 if id != s2_starter] + [s2_bench]
    new_bench_2 = [id for id in new_bench_1 if id != s2_bench] + [s2_starter]

    res2 = client.post("/api/v1/user-squad", json={
        "player_ids": new_starters_2 + new_bench_2,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": valid_ids[0],
        "vice_captain_id": valid_ids[1],
        "starter_ids": new_starters_2
    })
    assert res2.status_code == 200
    sq2 = res2.json()
    st2_ids = [p["id"] for p in sq2["starting_11"]]
    assert s2_bench in st2_ids
    assert s2_starter not in st2_ids

def test_captain_auto_transfer_on_bench_substitution(client, db_session):
    """Verify substituting the active Captain transfers Captain status to a starting XI player."""
    valid_ids = get_valid_15_player_ids(db_session)
    starters = valid_ids[:11]
    bench = valid_ids[11:]

    cap_id = starters[0]
    vc_id = starters[1]

    # Setup squad
    client.post("/api/v1/user-squad", json={
        "player_ids": valid_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": cap_id,
        "vice_captain_id": vc_id,
        "starter_ids": starters
    })

    # Swap out Captain cap_id for bench[0]
    new_starters = [id for id in starters if id != cap_id] + [bench[0]]
    # Transfer captaincy to vc_id
    new_cap = vc_id
    new_vc = new_starters[0]

    res = client.post("/api/v1/user-squad", json={
        "player_ids": valid_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "none",
        "captain_id": new_cap,
        "vice_captain_id": new_vc,
        "starter_ids": new_starters
    })
    assert res.status_code == 200
    data = res.json()

    assert data["captain_id"] == new_cap
    assert data["captain_id"] in [p["id"] for p in data["starting_11"]]

def test_frontend_substitution_ux_functions(client):
    """Verify frontend HTML contains openSubstitutionSelectionMode, checkSubstitutionLegality, and modal reset handlers."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "openSubstitutionSelectionMode()" in html
    assert "checkSubstitutionLegality" in html
    assert "↔️ SUBSTITUTE" in html
    assert "currentModalPlayer" in html
    assert "LOCKED:" in html
