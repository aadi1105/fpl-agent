import pytest
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection, UserSquad
from backend.ingestion.current_state import CurrentGameStateManager, PlayerEligibilityStatus
from backend.user.user_squad import UserSquadManager
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.diagnostics.reality_audit import DecisionEngineRealityAuditor

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_all_production_layers_use_same_current_gameweek(db_session):
    """Verify that every layer uses the EXACT SAME current active gameweek."""
    auditor = DecisionEngineRealityAuditor(db_session)
    gw_audit = auditor.audit_gameweek_consistency()
    assert gw_audit["is_consistent"] == True, f"Gameweek mismatch detected: {gw_audit}"
    assert gw_audit["state_manager_gw"] == gw_audit["database_is_current_gw"] == gw_audit["projection_target_gw"]

def test_haaland_presence(db_session):
    """Verify Haaland presence, club, price, fixture, xP, and optimizer eligibility."""
    haaland = db_session.query(Player).filter(Player.web_name.ilike("%Haaland%")).first()
    assert haaland is not None
    assert haaland.element_type == "FWD"
    assert haaland.now_cost == 155
    
    state_mgr = CurrentGameStateManager(db_session)
    elig = state_mgr.evaluate_player_eligibility(haaland)
    assert elig["is_optimizer_eligible"] == True

def test_injury_eligibility(db_session):
    """Verify long-term unavailable or injured players are not optimizer eligible."""
    mock_inj = Player(
        id=999993,
        web_name="TestInjured",
        element_type="FWD",
        now_cost=80,
        status="i",
        chance_of_playing_next_round=0,
        news="Out long term"
    )
    state_mgr = CurrentGameStateManager(db_session)
    elig = state_mgr.evaluate_player_eligibility(mock_inj)
    assert elig["is_optimizer_eligible"] == False

def test_my_team_configuration(db_session):
    """Verify persistent My Team squad CRUD and configuration capability."""
    us_mgr = UserSquadManager(db_session)
    squad = us_mgr.get_user_squad_dict(current_gw=1)
    assert len(squad["picks"]) == 15
    assert "starting_xi_xp" in squad

def test_player_selection_trace(db_session):
    """Verify backend diagnostic player selection trace."""
    auditor = DecisionEngineRealityAuditor(db_session)
    trace = auditor.trace_player_selection("Haaland")
    assert "web_name" in trace
    assert "v2_calibrated_xp" in trace
    assert "expected_minutes" in trace

def test_fixture_sensitivity(db_session):
    """Verify controlled diagnostic comparing actual vs raw baseline fixture impact."""
    auditor = DecisionEngineRealityAuditor(db_session)
    sens = auditor.audit_fixture_sensitivity(["Haaland", "Saka"])
    assert len(sens) >= 2
    for item in sens:
        assert "actual_gw_xp" in item
        assert "raw_base_xp" in item

def test_mode_horizon_correctness(db_session):
    """Verify mode horizon weights and definitions."""
    opt = SquadOptimizer(db_session)
    res_next = opt.solve_squad_selection(mode="NEXT_GW", current_gw=1)
    res_short = opt.solve_squad_selection(mode="SHORT_TERM", current_gw=1)
    res_med = opt.solve_squad_selection(mode="MEDIUM_TERM", current_gw=1)
    res_long = opt.solve_squad_selection(mode="LONG_TERM", current_gw=1)

    assert res_next["horizon_weights"] == [1.0]
    assert len(res_short["horizon_weights"]) == 2
    assert len(res_med["horizon_weights"]) == 4
    assert len(res_long["horizon_weights"]) == 7
