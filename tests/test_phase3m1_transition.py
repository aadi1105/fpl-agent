import pytest
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection, UserSquad
from backend.ingestion.current_state import CurrentGameStateManager, PlayerEligibilityStatus
from backend.user.user_squad import UserSquadManager
from backend.optimizer.squad_optimizer import SquadOptimizer

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_gw1_to_gw2_transition(db_session):
    """Explicitly verify GW1 -> GW2 gameweek transition."""
    state_mgr = CurrentGameStateManager(db_session)
    gw1_snapshot = state_mgr.generate_current_state_snapshot(season="2026-27")
    assert gw1_snapshot["snapshot_version"] == "2026_27_GW1_STATE_v1"

    # Advance to GW2
    adv_res = state_mgr.advance_gameweek(target_gw=2)
    assert adv_res["status"] == "ADVANCED"
    assert adv_res["current_gw"] == 2
    assert adv_res["snapshot_version"] == "2026_27_GW2_STATE_v1"

    current_gw = state_mgr.get_current_gameweek()
    assert current_gw == 2, "Current active gameweek must be GW2"

def test_historical_snapshot_immutability(db_session):
    """Verify GW1 snapshot and historical DB observations remain untouched after GW2 activation."""
    state_mgr = CurrentGameStateManager(db_session)
    gw1 = db_session.query(Gameweek).filter(Gameweek.id == 1).first()
    assert gw1 is not None
    assert gw1.is_previous == True, "GW1 must be marked as previous/historical"

    gw2 = db_session.query(Gameweek).filter(Gameweek.id == 2).first()
    assert gw2 is not None
    assert gw2.is_current == True, "GW2 must be marked as current"

def test_refresh_idempotency(db_session):
    """Verify refresh pipeline is idempotent and safe to execute multiple times."""
    state_mgr = CurrentGameStateManager(db_session)
    ref1 = state_mgr.refresh_current_gameweek()
    ref2 = state_mgr.refresh_current_gameweek()

    assert ref1["current_gw"] == ref2["current_gw"] == 2
    assert ref1["snapshot_version"] == ref2["snapshot_version"] == "2026_27_GW2_STATE_v1"
    assert ref1["summary"]["total_players"] == ref2["summary"]["total_players"]

def test_user_squad_persistence(db_session):
    """Verify persistent My Team squad creation and retrieval."""
    us_mgr = UserSquadManager(db_session)
    my_squad = us_mgr.get_user_squad_dict(current_gw=2)
    assert len(my_squad["picks"]) == 15, "My Team squad must contain 15 players"
    assert "total_cost_str" in my_squad
    assert "starting_xi_xp" in my_squad

def test_my_team_vs_optimal_comparison(db_session):
    """Verify My Team vs Optimal Team comparative tags (KEEP, TRANSFER IN, TRANSFER OUT)."""
    us_mgr = UserSquadManager(db_session)
    opt = SquadOptimizer(db_session)
    opt_res = opt.solve_squad_selection(mode="MEDIUM_TERM", current_gw=2)

    comp = us_mgr.compare_with_optimal_squad(optimal_result=opt_res, current_gw=2)
    assert "transfers_out" in comp
    assert "transfers_in" in comp
    assert "keeps_count" in comp
    assert "xp_gain" in comp

def test_optimization_modes_differentiation(db_session):
    """Verify NEXT_GW, SHORT_TERM, MEDIUM_TERM, and LONG_TERM modes use distinct mathematical horizons."""
    opt = SquadOptimizer(db_session)
    
    res_next = opt.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    res_short = opt.solve_squad_selection(mode="SHORT_TERM", current_gw=2)
    res_med = opt.solve_squad_selection(mode="MEDIUM_TERM", current_gw=2)
    res_long = opt.solve_squad_selection(mode="LONG_TERM", current_gw=2)

    assert res_next["horizon_weights"] == [1.0]
    assert len(res_short["horizon_weights"]) == 2
    assert len(res_med["horizon_weights"]) == 4
    assert len(res_long["horizon_weights"]) == 7

    # Cleanup: restore GW1 as current for default state
    state_mgr = CurrentGameStateManager(db_session)
    state_mgr.advance_gameweek(target_gw=1)
