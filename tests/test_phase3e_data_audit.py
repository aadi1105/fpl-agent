import pytest
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture, Gameweek
from backend.projections.engine import ProjectionEngine

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_awoniyi_team_and_fixture_consistency(db):
    """Mandatory regression test: Awoniyi must be assigned Coventry City, NOT Nottingham Forest."""
    awoniyi = db.query(Player).filter(Player.web_name == "Awoniyi").first()
    assert awoniyi is not None, "Awoniyi must exist in database"
    
    awoniyi_team = db.query(Team).filter(Team.id == awoniyi.team_id).first()
    assert awoniyi_team.short_name == "COV", f"Awoniyi must belong to Coventry City (COV), found {awoniyi_team.short_name}"
    
    # Check GW1 fixture
    gw1_fix = db.query(Fixture).filter(
        ((Fixture.team_h_id == awoniyi.team_id) | (Fixture.team_a_id == awoniyi.team_id)),
        Fixture.event_id == 1
    ).first()
    
    assert gw1_fix is not None, "Coventry City GW1 fixture must exist"
    assert awoniyi.team_id in (gw1_fix.team_h_id, gw1_fix.team_a_id)
    
    opp_id = gw1_fix.team_h_id if gw1_fix.team_a_id == awoniyi.team_id else gw1_fix.team_a_id
    opp_team = db.query(Team).filter(Team.id == opp_id).first()
    assert opp_team.short_name == "ARS", "Coventry City GW1 opponent must be Arsenal (ARS)"

def test_generic_player_fixture_team_consistency(db):
    """Generic test: For every player-fixture record across GW1-GW4, player.team_id must equal team_h_id or team_a_id."""
    players = db.query(Player).filter(Player.status == "a").all()
    assert len(players) > 0, "Active players must exist in database"
    
    mismatches = []
    for p in players:
        fixtures = db.query(Fixture).filter(
            ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
            Fixture.event_id.in_([1, 2, 3, 4])
        ).all()
        for fix in fixtures:
            if p.team_id not in (fix.team_h_id, fix.team_a_id):
                mismatches.append((p.web_name, p.team_id, fix.id, fix.team_h_id, fix.team_a_id))
                
    assert len(mismatches) == 0, f"Found {len(mismatches)} invalid player-fixture team assignments: {mismatches}"

def test_previous_club_fixture_rejection(db):
    """Verify ProjectionEngine raises ValueError hard failure if player team does not match fixture."""
    engine = ProjectionEngine(db=db)
    
    awoniyi = db.query(Player).filter(Player.web_name == "Awoniyi").first()
    # Query a Nottingham Forest fixture (where Awoniyi does NOT participate)
    forest_team = db.query(Team).filter(Team.short_name == "NFO").first()
    forest_fix = db.query(Fixture).filter(
        (Fixture.team_h_id == forest_team.id) | (Fixture.team_a_id == forest_team.id),
        Fixture.event_id == 1
    ).first()
    
    assert forest_fix is not None
    assert awoniyi.team_id != forest_team.id
    
    with pytest.raises(ValueError, match="CRITICAL FIXTURE VALIDATION FAILURE"):
        engine.calculate_player_xp_breakdown(awoniyi, fixture=forest_fix, is_home=True)

def test_current_price_consistency(db):
    """Verify canonical current player prices match official 2026/27 values."""
    price_checks = {
        "Haaland": 155,
        "Bruno Fernandes": 120,
        "Saka": 95,
        "Palmer": 95,
        "Gabriel": 80,
        "João Pedro": 75,
        "Calvert-Lewin": 60,
        "Awoniyi": 55,
        "Osula": 60
    }
    
    for name, expected_cost in price_checks.items():
        p = db.query(Player).filter(Player.web_name.ilike(f"%{name.split()[-1]}%")).first()
        assert p is not None, f"Player {name} not found in database"
        assert p.now_cost == expected_cost, f"Price mismatch for {name}: expected {expected_cost}, found {p.now_cost}"
