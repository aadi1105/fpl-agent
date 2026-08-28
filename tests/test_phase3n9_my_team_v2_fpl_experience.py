import pytest
import os
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, UserSquad, UserPick

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
# PHASE 3N.9 — MY TEAM V2 DEDICATED PAGE & SCHEMA TESTS
# ==================================================

def test_user_squad_v2_schema_and_ratings(client):
    """Verify GET /api/v1/user-squad returns V2 fields including bench_xp, squad_total_xp, team_rating."""
    res = client.get("/api/v1/user-squad")
    assert res.status_code == 200
    data = res.json()
    assert "is_configured" in data
    assert "starting_xi_xp" in data
    assert "bench_xp" in data
    assert "squad_total_xp" in data
    assert "team_rating" in data
    assert "team_rating_breakdown" in data
    assert "picks" in data

def test_update_user_squad_starters_and_captaincy(client, db_session):
    """Verify POST /api/v1/user-squad persists starter_ids, captain_id, vice_captain_id, bank, FTs."""
    all_players = db_session.query(Player).limit(100).all()
    gkps = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    saved_ids = gkps + defs + mids + fwds

    # 11 starters: 1 GKP, 3 DEF, 4 MID, 3 FWD
    starter_ids = [gkps[0]] + defs[:3] + mids[:4] + fwds[:3]
    cap_id = starter_ids[1]
    vc_id = starter_ids[2]

    payload = {
        "player_ids": saved_ids,
        "bank": 10,  # £1.0m
        "free_transfers": 2,
        "active_chip": "bboost",
        "captain_id": cap_id,
        "vice_captain_id": vc_id,
        "starter_ids": starter_ids
    }

    res = client.post("/api/v1/user-squad", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["bank"] == 10
    assert data["free_transfers"] == 2
    assert data["active_chip"] == "bboost"

    picks = data["picks"]
    cap_pick = next(p for p in picks if p["id"] == cap_id)
    vc_pick = next(p for p in picks if p["id"] == vc_id)

    assert cap_pick["is_captain"] is True
    assert cap_pick["multiplier"] == 2
    assert vc_pick["is_vice_captain"] is True

    # Starters vs Bench count
    starters = [p for p in picks if p["is_starter"]]
    bench = [p for p in picks if not p["is_starter"]]
    assert len(starters) == 11
    assert len(bench) == 4

def test_active_chip_triple_captain_multiplier(client, db_session):
    """Verify active_chip='triplecaptain' sets captain multiplier to 3."""
    all_players = db_session.query(Player).limit(100).all()
    gkps = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    saved_ids = gkps + defs + mids + fwds

    cap_id = gkps[0]
    payload = {
        "player_ids": saved_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": "triplecaptain",
        "captain_id": cap_id
    }

    res = client.post("/api/v1/user-squad", json=payload)
    assert res.status_code == 200
    data = res.json()
    cap_pick = next(p for p in data["picks"] if p["id"] == cap_id)
    assert cap_pick["multiplier"] == 3

def test_invalid_squad_size_rejection(client):
    """Verify POST /api/v1/user-squad with <15 player IDs is rejected."""
    payload = {
        "player_ids": [1, 2, 3, 4, 5],
        "bank": 0,
        "free_transfers": 1
    }
    res = client.post("/api/v1/user-squad", json=payload)
    assert res.status_code == 500

def test_unconfigured_squad_returns_zero_and_empty_picks(client):
    """Verify unconfigured squad state returns clean zeros without fake squads."""
    # Clear squad
    from backend.models import UserPick, UserSquad
    db = SessionLocal()
    db.query(UserPick).delete()
    db.query(UserSquad).delete()
    db.add(UserSquad(id=1, name="My FPL Team", bank=0, free_transfers=1, active_chip=None))
    db.commit()
    db.close()

    res = client.get("/api/v1/user-squad")
    assert res.status_code == 200
    data = res.json()
    assert data["is_configured"] is False
    assert len(data["picks"]) == 0
    assert data["starting_xi_xp"] == 0.0
    assert data["team_rating"] == 0.0
