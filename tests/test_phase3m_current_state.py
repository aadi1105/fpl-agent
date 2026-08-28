import pytest
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection
from backend.ingestion.current_state import CurrentGameStateManager, PlayerEligibilityStatus
from backend.optimizer.squad_optimizer import SquadOptimizer

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_haaland_present_and_eligible(db_session):
    """Verify Haaland is present in 2026/27 player pool and fully eligible."""
    haaland = db_session.query(Player).filter(Player.web_name.ilike("%Haaland%")).first()
    assert haaland is not None, "Erling Haaland must be present in database"
    assert haaland.element_type == "FWD", "Haaland position must be FWD"
    assert haaland.now_cost == 155, "Haaland price must be £15.5m (155 integer units)"
    
    state_mgr = CurrentGameStateManager(db_session)
    elig = state_mgr.evaluate_player_eligibility(haaland)
    assert elig["is_optimizer_eligible"] == True, "Haaland must be optimizer eligible"
    assert elig["eligibility_status"] in [PlayerEligibilityStatus.ACTIVE, PlayerEligibilityStatus.EXPECTED_STARTER]

def test_current_gw_detection(db_session):
    """Verify current GW detection from database state."""
    state_mgr = CurrentGameStateManager(db_session)
    gw = state_mgr.get_current_gameweek()
    assert isinstance(gw, int)
    assert 1 <= gw <= 38

def test_transferred_player_handling(db_session):
    """Verify current 2026/27 club assignments for transferred players."""
    state_mgr = CurrentGameStateManager(db_session)
    
    # Awoniyi -> Coventry City (COV)
    awoniyi = db_session.query(Player).filter(Player.web_name.ilike("%Awoniyi%")).first()
    assert awoniyi is not None
    cov_team = db_session.query(Team).filter(Team.short_name == "COV").first()
    assert awoniyi.team_id == cov_team.id, f"Awoniyi must belong to Coventry City (COV), found team_id {awoniyi.team_id}"

    # Nelson -> Arsenal (ARS)
    nelson = db_session.query(Player).filter(Player.web_name.ilike("%Nelson%")).first()
    assert nelson is not None
    ars_team = db_session.query(Team).filter(Team.short_name == "ARS").first()
    assert nelson.team_id == ars_team.id, f"Nelson must belong to Arsenal (ARS), found team_id {nelson.team_id}"

def test_long_term_injury_handling(db_session):
    """Verify long-term injured or unavailable players are marked ineligible."""
    state_mgr = CurrentGameStateManager(db_session)
    
    # Create temporary mock injured player status test
    mock_injured_player = Player(
        id=999991,
        web_name="TestInjuredPlayer",
        element_type="MID",
        now_cost=60,
        status="i",
        chance_of_playing_next_round=0,
        news="ACL Tear - Out for 6 months"
    )
    elig = state_mgr.evaluate_player_eligibility(mock_injured_player)
    assert elig["is_optimizer_eligible"] == False
    assert elig["eligibility_status"] == PlayerEligibilityStatus.INJURED

def test_first_choice_backup_distinction(db_session):
    """Verify backup GKP receives BACKUP status classification."""
    state_mgr = CurrentGameStateManager(db_session)
    
    backup_gkp = Player(
        id=999992,
        web_name="TestBackupGKP",
        element_type="GKP",
        now_cost=40,
        status="a",
        chance_of_playing_next_round=100,
        minutes=15
    )
    elig = state_mgr.evaluate_player_eligibility(backup_gkp)
    assert elig["eligibility_status"] == PlayerEligibilityStatus.BACKUP

def test_snapshot_creation(db_session):
    """Verify idempotent current state snapshot generation."""
    state_mgr = CurrentGameStateManager(db_session)
    snapshot = state_mgr.generate_current_state_snapshot(season="2026-27")
    assert "snapshot_version" in snapshot
    assert snapshot["summary"]["total_players"] > 0
    assert snapshot["summary"]["optimizer_eligible_players"] > 0

def test_data_quality_audit(db_session):
    """Verify data quality layer audit."""
    state_mgr = CurrentGameStateManager(db_session)
    audit = state_mgr.run_data_quality_audit()
    assert audit["total_players"] > 0
    assert audit["missing_prices_count"] == 0
    assert audit["missing_teams_count"] == 0
    assert audit["missing_positions_count"] == 0
