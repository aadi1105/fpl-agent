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
# PHASE 3N.23 — IMMUTABLE SNAPSHOTS & SEASON HISTORY TESTS
# ==================================================

def test_bench_points_are_resolved_from_live_data(client, db_session):
    """Verify bench players' actual points are resolved from live data (not multiplied by 0)."""
    res = client.get("/api/v1/user-squad/gameweek/1")
    assert res.status_code == 200
    snap = res.json()

    assert snap["bench_points"] == 21  # Exact sum of live bench points (14 + 3 + 1 + 3 = 21)
    bench = snap["bench"]
    assert len(bench) == 4

    for p in bench:
        assert "actual_pts" in p
        assert p["actual_pts"] is not None

    sangare = next((p for p in bench if "Sangar" in p["web_name"]), None)
    if sangare:
        assert sangare["actual_pts"] == 14

def test_missing_points_are_not_silently_zero(client):
    """Verify future Gameweek (GW3) returns actual_pts == None rather than fake 0."""
    res = client.get("/api/v1/user-squad/gameweek/3")
    assert res.status_code == 200
    snap = res.json()

    assert snap["starting_xi_points"] is None
    assert snap["bench_points"] is None
    for p in snap["starting_11"]:
        assert p["actual_pts"] is None

def test_historical_snapshot_contains_all_15_players(client):
    """Verify completed snapshot contains exactly 15 unique players (11 starters, 4 bench)."""
    res = client.get("/api/v1/user-squad/gameweek/1")
    assert res.status_code == 200
    snap = res.json()

    starters = snap["starting_11"]
    bench = snap["bench"]
    assert len(starters) == 11
    assert len(bench) == 4

    all_ids = {p["id"] for p in starters + bench}
    assert len(all_ids) == 15

def test_completed_gw_snapshot_is_immutable(client, db_session):
    """Verify completed GW1 snapshot persists as a frozen GameweekTeamSnapshot in DB."""
    res = client.get("/api/v1/user-squad/gameweek/1")
    assert res.status_code == 200

    frozen = db_session.query(GameweekTeamSnapshot).filter(
        GameweekTeamSnapshot.gameweek_id == 1,
        GameweekTeamSnapshot.is_final == True
    ).first()
    assert frozen is not None
    assert frozen.net_gw_score in [39, 54]
    assert frozen.bench_points == 21

def test_current_transfer_does_not_mutate_gw1_snapshot(client, db_session):
    """
    MANDATORY ACCEPTANCE TEST:
    Updating current squad (e.g. transferring Haaland -> Salah) MUST NEVER mutate GW1 snapshot!
    """
    # 1. Ensure UserSquad is configured
    mgr = UserSquadManager(db_session)
    curr_sq = mgr.get_user_squad_dict()
    if not curr_sq["is_configured"]:
        gkps = [p.id for p in db_session.query(Player).filter(Player.element_type == "GKP").limit(2).all()]
        defs = [p.id for p in db_session.query(Player).filter(Player.element_type == "DEF").limit(5).all()]
        mids = [p.id for p in db_session.query(Player).filter(Player.element_type == "MID").limit(5).all()]
        fwds = [p.id for p in db_session.query(Player).filter(Player.element_type == "FWD").limit(3).all()]
        all_15 = gkps + defs + mids + fwds
        starters = [gkps[0]] + defs[:3] + mids[:4] + fwds[:3]
        mgr.update_user_squad(
            player_ids=all_15,
            bank=0,
            free_transfers=1,
            active_chip=None,
            captain_id=fwds[0],
            vice_captain_id=mids[0],
            starter_ids=starters
        )
        curr_sq = mgr.get_user_squad_dict()

    # 2. Fetch GW1 snapshot and capture player IDs
    res1 = client.get("/api/v1/user-squad/gameweek/1")
    assert res1.status_code == 200
    gw1_orig_pids = [p["id"] for p in res1.json()["picks"]]

    # 3. Perform transfer in Current Squad (replace player 1 with another valid player)
    curr_ids = [p["id"] for p in curr_sq["picks"]]
    alt_player = db_session.query(Player).filter(~Player.id.in_(curr_ids), Player.element_type == "FWD").first()
    assert alt_player is not None

    new_curr_ids = list(curr_ids)
    new_curr_ids[0] = alt_player.id  # Transfer out 1st player

    # Save mutated current squad
    mgr.update_user_squad(
        player_ids=new_curr_ids,
        bank=0,
        free_transfers=1,
        active_chip=None,
        captain_id=new_curr_ids[0],
        vice_captain_id=new_curr_ids[1],
        starter_ids=new_curr_ids[:11]
    )

    # 4. Re-fetch GW1 snapshot -> MUST STILL CONTAIN ORIGINAL GW1 PLAYER IDS!
    res1_after = client.get("/api/v1/user-squad/gameweek/1")
    assert res1_after.status_code == 200
    gw1_after_pids = [p["id"] for p in res1_after.json()["picks"]]

    assert gw1_after_pids == gw1_orig_pids  # GW1 REMAINS 100% IMMUTABLE!

    # 5. Fetch Current Squad -> CONTAINS THE NEW TRANSFERRED PLAYER!
    res_curr_after = client.get("/api/v1/user-squad")
    assert res_curr_after.status_code == 200
    curr_after_pids = [p["id"] for p in res_curr_after.json()["picks"]]
    assert alt_player.id in curr_after_pids
    assert alt_player.id not in gw1_after_pids

def test_season_history_table_aggregates_correctly(client):
    """Verify GET /api/v1/user-squad/season-history returns summary metrics, chips status, and 38 GW rows."""
    res = client.get("/api/v1/user-squad/season-history")
    assert res.status_code == 200
    data = res.json()

    assert "summary_metrics" in data
    assert "chips_status" in data
    assert "history_rows" in data

    metrics = data["summary_metrics"]
    assert metrics["total_points"] in [39, 54]
    assert metrics["gw_avg"] in [39.0, 54.0]

    chips = data["chips_status"]
    assert len(chips) == 4
    keys = {c["key"] for c in chips}
    assert keys == {"wildcard", "freehit", "benchboost", "triplecaptain"}

    rows = data["history_rows"]
    assert len(rows) == 38
    assert rows[0]["gw"] == 1
    assert rows[0]["status"] == "COMPLETED"
    assert rows[0]["net_gw_score"] in [39, 54]
    assert rows[0]["bench_points"] == 21
