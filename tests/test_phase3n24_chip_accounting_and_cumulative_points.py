import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, UserSquad, GameweekTeamSnapshot
from backend.user.user_squad import UserSquadManager
from backend.services.fpl_history_service import FPLHistoryService

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
# PHASE 3N.24 — CHIP ACCOUNTING & CUMULATIVE POINTS TESTS
# ==================================================

SAVED_STARTER_IDS = [411, 426, 427, 1, 8, 368, 346, 87, 423, 165, 565]
SAVED_BENCH_IDS = [124, 173, 175, 496]
SAVED_15_IDS = SAVED_STARTER_IDS + SAVED_BENCH_IDS

def ensure_saved_squad(db_session, chip="benchboost"):
    mgr = UserSquadManager(db_session)
    sq = mgr.get_or_create_user_squad()
    mgr.update_user_squad(
        player_ids=SAVED_15_IDS,
        bank=0,
        free_transfers=1,
        active_chip=chip,
        captain_id=426,      # B.Fernandes
        vice_captain_id=411, # Haaland
        starter_ids=SAVED_STARTER_IDS
    )
    # Ensure GW1 snapshot has active_chip = 'none' and net_gw_score = 54
    gw1_snap = db_session.query(GameweekTeamSnapshot).filter(GameweekTeamSnapshot.gameweek_id == 1, GameweekTeamSnapshot.is_final == True).first()
    if gw1_snap:
        gw1_snap.active_chip = "none"
        gw1_snap.net_gw_score = 54
        db_session.commit()

def test_bench_boost_points_are_included_in_final_score(client, db_session):
    """Verify Bench Boost includes all 15 players (starting XI + bench) in final Gameweek score."""
    ensure_saved_squad(db_session, chip="benchboost")

    # Clear frozen GW2 snapshot so we re-evaluate live
    db_session.query(GameweekTeamSnapshot).filter(GameweekTeamSnapshot.gameweek_id == 2).delete()
    db_session.commit()

    res = client.get("/api/v1/user-squad/gameweek/2")
    assert res.status_code == 200
    snap = res.json()

    assert snap["active_chip"] == "benchboost"
    assert snap["bench_points"] == 24
    assert snap["starting_xi_points"] == 100
    assert snap["net_gw_score"] == 124  # 100 starting XI + 24 bench = 124

def test_bench_boost_score_equals_starting_xi_plus_captain_bonus_plus_bench(client, db_session):
    """Verify 77 raw starting XI + 23 captain bonus + 24 bench = 124 total score."""
    ensure_saved_squad(db_session, chip="benchboost")

    res = client.get("/api/v1/user-squad/gameweek/2")
    assert res.status_code == 200
    snap = res.json()

    starters_raw = sum(p["actual_pts"] for p in snap["starting_11"] if p.get("actual_pts") is not None)
    cap_bonus = snap["captain_bonus"]
    bench_sum = sum(p["actual_pts"] for p in snap["bench"] if p.get("actual_pts") is not None)

    assert starters_raw == 77
    assert cap_bonus == 23
    assert bench_sum == 24
    assert snap["net_gw_score"] == starters_raw + cap_bonus + bench_sum  # 77 + 23 + 24 = 124

def test_captain_bonus_is_not_double_counted(client, db_session):
    """Verify Captain raw (23) is counted once in raw sum (77) and +23 bonus added, giving starting XI 100."""
    ensure_saved_squad(db_session, chip="benchboost")

    res = client.get("/api/v1/user-squad/gameweek/2")
    assert res.status_code == 200
    snap = res.json()

    assert snap["starting_xi_points"] == 100  # NOT 123 (which would be double counted!)

def test_gw2_expected_score_is_124_for_current_fixture_data(client, db_session):
    """Verify GW2 score equals exactly 124 for the current fixture data."""
    ensure_saved_squad(db_session, chip="benchboost")

    res = client.get("/api/v1/user-squad/gameweek/2")
    assert res.status_code == 200
    snap = res.json()

    assert snap["net_gw_score"] == 124

def test_active_chip_persists_after_refresh(client, db_session):
    """Verify active_chip persists in DB and across API requests."""
    ensure_saved_squad(db_session, chip="benchboost")

    res = client.get("/api/v1/user-squad")
    assert res.status_code == 200
    squad_data = res.json()

    assert squad_data["active_chip"] == "benchboost"
    assert "used_chips_map" in squad_data
    assert squad_data["used_chips_map"].get("benchboost") == 2

def test_used_chip_removed_from_available_chips(client, db_session):
    """Verify used chips map lists Bench Boost as used in GW2."""
    ensure_saved_squad(db_session, chip="benchboost")

    res = client.get("/api/v1/user-squad/season-history")
    assert res.status_code == 200
    data = res.json()

    bb_chip = next((c for c in data["chips_status"] if c["key"] == "benchboost"), None)
    assert bb_chip is not None
    assert bb_chip["status"] == "USED — GW2"
    assert bb_chip["is_used"] is True

def test_overall_points_are_cumulative(client, db_session):
    """Verify overall points are cumulative: GW1 (54) + GW2 (124) = 178."""
    ensure_saved_squad(db_session, chip="benchboost")

    # Ensure GW1 snapshot has 54 points
    gw1_snap = db_session.query(GameweekTeamSnapshot).filter(GameweekTeamSnapshot.gameweek_id == 1, GameweekTeamSnapshot.is_final == True).first()
    if gw1_snap:
        gw1_snap.net_gw_score = 54
        db_session.commit()

    res = client.get("/api/v1/user-squad/season-history")
    assert res.status_code == 200
    data = res.json()

    rows = data["history_rows"]
    assert rows[0]["gw"] == 1
    assert rows[0]["overall_points"] == 54

    assert rows[1]["gw"] == 2
    assert rows[1]["net_gw_score"] == 124
    assert rows[1]["overall_points"] == 178

    metrics = data["summary_metrics"]
    assert metrics["total_points"] == 178

def test_future_gameweeks_preserve_latest_cumulative_total(client, db_session):
    """Verify future Gameweeks (GW3+) preserve the latest cumulative total (178) rather than 0."""
    ensure_saved_squad(db_session, chip="benchboost")

    res = client.get("/api/v1/user-squad/season-history")
    assert res.status_code == 200
    data = res.json()

    rows = data["history_rows"]
    for r in rows[2:]:  # GW3..38
        assert r["status"] == "UPCOMING"
        assert r["overall_points"] == 178
        assert r["net_gw_score"] is None

def test_rank_is_not_fabricated_when_unavailable(client):
    """Verify unlinked local manager returns 'NOT_LINKED' instead of empty dashes or fabricated numbers."""
    res = client.get("/api/v1/user-squad/season-history")
    assert res.status_code == 200
    data = res.json()

    assert data["summary_metrics"]["current_rank"] == "NOT_LINKED"
    assert data["history_rows"][0]["overall_rank"] == "NOT_LINKED"

def test_chip_state_is_gameweek_specific(client, db_session):
    """Verify GW1 chip is NONE while GW2 chip is BENCH BOOST."""
    ensure_saved_squad(db_session, chip="benchboost")

    # Set GW1 snapshot to active_chip = 'none'
    gw1_snap = db_session.query(GameweekTeamSnapshot).filter(GameweekTeamSnapshot.gameweek_id == 1, GameweekTeamSnapshot.is_final == True).first()
    if gw1_snap:
        gw1_snap.active_chip = "none"
        db_session.commit()

    res1 = client.get("/api/v1/user-squad/gameweek/1")
    assert res1.status_code == 200
    assert res1.json()["active_chip"] == "none"

    res2 = client.get("/api/v1/user-squad/gameweek/2")
    assert res2.status_code == 200
    assert res2.json()["active_chip"] == "benchboost"

def test_completed_snapshot_remains_immutable_after_current_squad_edit(client, db_session):
    """Verify mutating current squad for GW3 does NOT alter GW1 snapshot."""
    ensure_saved_squad(db_session, chip="benchboost")

    res1 = client.get("/api/v1/user-squad/gameweek/1")
    assert res1.status_code == 200
    gw1_orig_pids = [p["id"] for p in res1.json()["picks"]]

    mgr = UserSquadManager(db_session)
    curr_sq = mgr.get_user_squad_dict()
    curr_ids = [p["id"] for p in curr_sq["picks"]]

    alt_player = db_session.query(Player).filter(~Player.id.in_(curr_ids), Player.element_type == "FWD").first()
    assert alt_player is not None

    new_ids = list(curr_ids)
    new_ids[0] = alt_player.id
    mgr.update_user_squad(player_ids=new_ids, bank=0, free_transfers=1, active_chip=None, captain_id=new_ids[0], vice_captain_id=new_ids[1], starter_ids=new_ids[:11])

    res1_after = client.get("/api/v1/user-squad/gameweek/1")
    assert res1_after.status_code == 200
    gw1_after_pids = [p["id"] for p in res1_after.json()["picks"]]

    assert gw1_after_pids == gw1_orig_pids
