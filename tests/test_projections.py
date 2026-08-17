import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Team, Player, Gameweek, Fixture, ElementType, PlayerProjection
from backend.projections.engine import ProjectionEngine

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    
    t1 = Team(id=1, name="Arsenal", short_name="ARS", strength_attack_home=1200, strength_defence_home=1250)
    t2 = Team(id=2, name="Chelsea", short_name="CHE", strength_attack_away=1100, strength_defence_away=1050)
    session.add_all([t1, t2])
    
    gw1 = Gameweek(id=1, name="Gameweek 1", is_current=True)
    session.add(gw1)
    
    f1 = Fixture(id=1, event_id=1, team_h_id=1, team_a_id=2, team_h_difficulty=3, team_a_difficulty=4)
    session.add(f1)
    
    # Premium FWD (Haaland-like) vs Cheap DEF (Thiaw-like)
    haaland = Player(
        id=1, web_name="Haaland", team_id=1, element_type=ElementType.FWD.value,
        now_cost=150, status="a", minutes=900, total_points=120,
        expected_goals=10.0, expected_assists=2.0, bps=300
    )
    cheap_def = Player(
        id=2, web_name="CheapDef", team_id=1, element_type=ElementType.DEF.value,
        now_cost=45, status="a", minutes=900, total_points=40,
        expected_goals=0.2, expected_assists=0.3, defensive_contributions=60, bps=120
    )
    session.add_all([haaland, cheap_def])
    session.commit()
    
    yield session
    session.close()

def test_projection_engine_calibrated_ordering(db_session):
    engine = ProjectionEngine(db_session)
    count = engine.run_projections(start_gw=1, end_gw=1, source="internal")
    assert count == 2
    
    haaland_proj = db_session.query(PlayerProjection).filter_by(player_id=1, gameweek_id=1).first()
    cheap_def_proj = db_session.query(PlayerProjection).filter_by(player_id=2, gameweek_id=1).first()
    
    assert haaland_proj is not None
    assert cheap_def_proj is not None

    # Premium attacker MUST significantly outrank cheap defender in absolute expected points per match
    assert haaland_proj.expected_points > cheap_def_proj.expected_points + 2.0
    assert haaland_proj.expected_minutes >= 75.0

def test_arithmetic_component_breakdown(db_session):
    engine = ProjectionEngine(db_session)
    player = db_session.query(Player).filter_by(id=1).first()
    fixture = db_session.query(Fixture).filter_by(id=1).first()
    team = db_session.query(Team).filter_by(id=2).first()

    bd = engine.calculate_player_xp_breakdown(player, fixture, True, team)
    component_sum = bd["appearance_xp"] + bd["goals_xp"] + bd["assists_xp"] + bd["cs_xp"] + bd["defcon_xp"] + bd["saves_xp"] + bd["bonus_xp"] + bd["cards_xp"]
    
    assert abs(bd["total_xp"] - max(0.0, round(component_sum, 2))) < 0.05
