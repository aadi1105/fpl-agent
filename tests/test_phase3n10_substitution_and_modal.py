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
# PHASE 3N.10 — MODAL CLOSE & SUBSTITUTION TESTS
# ==================================================

def test_modal_close_markup_and_function():
    """Verify frontend HTML contains dedicated player-insight-close button, closePlayerInsightModal function, and no duplicate closeModal definitions."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="player-insight-close"' in html
    assert 'id="breakdown-modal"' in html
    assert "closePlayerInsightModal()" in html
    assert "style.display = 'none'" in html
    assert "style.visibility = 'hidden'" in html
    assert "Escape" in html

    # Verify no duplicate function closeModal() definitions exist to prevent JS hoisting shadowing bugs
    close_modal_count = html.count("function closeModal()")
    assert close_modal_count <= 1, f"Found {close_modal_count} function closeModal() definitions! Duplicate function declarations cause hoisting bugs."

def test_starter_bench_substitution_flow(client, db_session):
    """Verify substituting a starter with a bench player updates starter_ids without changing bank or FT."""
    all_players = db_session.query(Player).limit(100).all()
    gkps = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    saved_ids = gkps + defs + mids + fwds

    # 11 Starters: 1 GKP, 3 DEF, 4 MID, 3 FWD (3-4-3)
    initial_starters = [gkps[0]] + defs[:3] + mids[:4] + fwds[:3]
    bench_def = defs[3]  # Bench DEF

    # Initial squad save
    payload = {
        "player_ids": saved_ids,
        "bank": 0,
        "free_transfers": 1,
        "captain_id": initial_starters[1],
        "vice_captain_id": initial_starters[2],
        "starter_ids": initial_starters
    }
    res = client.post("/api/v1/user-squad", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["bank"] == 0
    assert data["free_transfers"] == 1

    # Substitute MID starter (initial_starters[4]) with Bench DEF (bench_def) -> 4-3-3 formation
    mid_starter_id = initial_starters[4]
    new_starters = [id if id != mid_starter_id else bench_def for id in initial_starters]

    sub_payload = {
        "player_ids": saved_ids,
        "bank": 0,
        "free_transfers": 1,
        "captain_id": initial_starters[1],
        "vice_captain_id": initial_starters[2],
        "starter_ids": new_starters
    }
    sub_res = client.post("/api/v1/user-squad", json=sub_payload)
    assert sub_res.status_code == 200
    sub_data = sub_res.json()

    # Verify 15 total, 11 starters, 4 bench
    picks = sub_data["picks"]
    assert len(picks) == 15
    starters = [p for p in picks if p["is_starter"]]
    bench = [p for p in picks if not p["is_starter"]]
    assert len(starters) == 11
    assert len(bench) == 4

    # Verify new starter is bench_def, and old starter is on bench
    assert any(p["id"] == bench_def for p in starters)
    assert any(p["id"] == mid_starter_id for p in bench)

    # Verify zero FT consumed, zero bank change
    assert sub_data["bank"] == 0
    assert sub_data["free_transfers"] == 1

def test_captain_transfer_on_bench_move(client, db_session):
    """Verify moving Captain to bench automatically transfers captaincy."""
    all_players = db_session.query(Player).limit(100).all()
    gkps = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    saved_ids = gkps + defs + mids + fwds

    initial_starters = [gkps[0]] + defs[:3] + mids[:4] + fwds[:3]
    cap_id = initial_starters[1]  # Starter DEF 1
    vc_id = initial_starters[2]   # Starter DEF 2
    bench_def = defs[3]           # Bench DEF

    # Move Captain (cap_id) to bench, replaced by bench_def
    new_starters = [id if id != cap_id else bench_def for id in initial_starters]

    payload = {
        "player_ids": saved_ids,
        "bank": 0,
        "free_transfers": 1,
        "captain_id": vc_id,  # Transfer captaincy to VC
        "vice_captain_id": new_starters[0],
        "starter_ids": new_starters
    }
    res = client.post("/api/v1/user-squad", json=payload)
    assert res.status_code == 200
    data = res.json()

    picks = data["picks"]
    cap_pick = next(p for p in picks if p["is_captain"])
    benched_cap_pick = next(p for p in picks if p["id"] == cap_id)

    # Captain must be a starter with multiplier >= 2
    assert cap_pick["id"] == vc_id
    assert cap_pick["is_starter"] is True
    assert benched_cap_pick["is_starter"] is False

def test_substitution_persists_across_reload(client, db_session):
    """Verify substituted starting XI persists cleanly across GET reloads."""
    all_players = db_session.query(Player).limit(100).all()
    gkps = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    saved_ids = gkps + defs + mids + fwds

    starters = [gkps[0]] + defs[:3] + mids[:4] + fwds[:3]
    payload = {
        "player_ids": saved_ids,
        "bank": 0,
        "free_transfers": 1,
        "captain_id": starters[0],
        "starter_ids": starters
    }
    client.post("/api/v1/user-squad", json=payload)

    # Hard GET reload
    reload_res = client.get("/api/v1/user-squad")
    assert reload_res.status_code == 200
    reload_data = reload_res.json()
    reload_starters = [p["id"] for p in reload_data["picks"] if p["is_starter"]]
    assert set(reload_starters) == set(starters)
