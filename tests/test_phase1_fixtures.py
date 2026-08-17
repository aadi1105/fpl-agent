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
    
    # Create Teams with distinct strengths
    # Arsenal (Strong Def, High Att), Ipswich (Weak Def, Low Att), Man City (Strong Att), Chelsea (Mid)
    t1 = Team(id=1, name="Arsenal", short_name="ARS", strength_attack_home=1250, strength_defence_home=1300, strength_attack_away=1200, strength_defence_away=1250)
    t2 = Team(id=2, name="Ipswich", short_name="IPS", strength_attack_home=900, strength_defence_home=850, strength_attack_away=850, strength_defence_away=800)
    t3 = Team(id=3, name="Man City", short_name="MCI", strength_attack_home=1350, strength_defence_home=1200, strength_attack_away=1300, strength_defence_away=1150)
    t4 = Team(id=4, name="Chelsea", short_name="CHE", strength_attack_home=1100, strength_defence_home=1050, strength_attack_away=1050, strength_defence_away=1000)
    session.add_all([t1, t2, t3, t4])
    
    gw1 = Gameweek(id=1, name="Gameweek 1", is_current=True)
    gw2 = Gameweek(id=2, name="Gameweek 2")
    gw3 = Gameweek(id=3, name="Gameweek 3")
    gw4 = Gameweek(id=4, name="Gameweek 4")
    session.add_all([gw1, gw2, gw3, gw4])

    # Fixtures where Arsenal (Team 1) has 4 distinct fixtures across GW1-GW4:
    # GW1: ARS (Home) vs IPS (Weak Def)
    # GW2: ARS (Away) vs MCI (Strong Att/Def)
    # GW3: ARS (Home) vs CHE (Mid)
    # GW4: ARS (Away) vs IPS (Weak Att)
    f1 = Fixture(id=1, event_id=1, team_h_id=1, team_a_id=2, team_h_difficulty=2, team_a_difficulty=5)
    f2 = Fixture(id=2, event_id=2, team_h_id=3, team_a_id=1, team_h_difficulty=4, team_a_difficulty=4)
    f3 = Fixture(id=3, event_id=3, team_h_id=1, team_a_id=4, team_h_difficulty=3, team_a_difficulty=3)
    f4 = Fixture(id=4, event_id=4, team_h_id=2, team_a_id=1, team_h_difficulty=2, team_a_difficulty=4)
    session.add_all([f1, f2, f3, f4])
    
    saka = Player(
        id=1, web_name="Saka", team_id=1, element_type=ElementType.MID.value,
        now_cost=100, status="a", minutes=900, total_points=100,
        expected_goals=8.0, expected_assists=5.0, bps=250
    )
    gabriel = Player(
        id=2, web_name="Gabriel", team_id=1, element_type=ElementType.DEF.value,
        now_cost=60, status="a", minutes=900, total_points=80,
        expected_goals=2.0, expected_assists=0.5, defensive_contributions=120, bps=200
    )
    session.add_all([saka, gabriel])
    session.commit()
    
    yield session
    session.close()

def test_fixture_aware_projections_differ_by_opponent_and_location(db_session):
    engine = ProjectionEngine(db_session)
    count = engine.run_projections(start_gw=1, end_gw=4, source="internal")
    assert count == 8  # 2 players * 4 GWs

    saka = db_session.query(Player).filter_by(id=1).first()
    t_ips = db_session.query(Team).filter_by(id=2).first()
    t_mci = db_session.query(Team).filter_by(id=3).first()

    f1 = db_session.query(Fixture).filter_by(id=1).first() # vs IPS Home
    f2 = db_session.query(Fixture).filter_by(id=2).first() # vs MCI Away

    bd1 = engine.calculate_player_xp_breakdown(saka, f1, True, t_ips)
    bd2 = engine.calculate_player_xp_breakdown(saka, f2, False, t_mci)

    # 1. Opponent verification
    assert bd1["opp_short_name"] == "IPS"
    assert bd1["is_home"] is True
    assert bd2["opp_short_name"] == "MCI"
    assert bd2["is_home"] is False

    # 2. Underlying xG & xA must be HIGHER against weak Ipswich defence at Home than against strong Man City defence Away
    assert bd1["xg_match"] > bd2["xg_match"]
    assert bd1["xa_match"] > bd2["xa_match"]
    assert bd1["goals_xp"] > bd2["goals_xp"]

def test_defcon_and_cleansheet_vary_by_fixture(db_session):
    engine = ProjectionEngine(db_session)
    gabriel = db_session.query(Player).filter_by(id=2).first()
    t_ips = db_session.query(Team).filter_by(id=2).first()
    t_mci = db_session.query(Team).filter_by(id=3).first()

    f1 = db_session.query(Fixture).filter_by(id=1).first() # vs IPS Home
    f2 = db_session.query(Fixture).filter_by(id=2).first() # vs MCI Away

    bd1 = engine.calculate_player_xp_breakdown(gabriel, f1, True, t_ips)
    bd2 = engine.calculate_player_xp_breakdown(gabriel, f2, False, t_mci)

    # Clean Sheet Probability MUST be higher against weak attacking Ipswich than strong attacking Man City
    assert bd1["cs_prob"] > bd2["cs_prob"]
    assert bd1["cs_xp"] > bd2["cs_xp"]

    # DEFCON Workload (CBIT) MUST be higher against high-attacking Man City than low-attacking Ipswich
    assert bd2["defcon_prob"] > bd1["defcon_prob"]

def test_projections_stored_per_gameweek(db_session):
    engine = ProjectionEngine(db_session)
    engine.run_projections(start_gw=1, end_gw=4, source="internal")

    projs = db_session.query(PlayerProjection).filter_by(player_id=1).all()
    assert len(projs) == 4
    gw_ids = [p.gameweek_id for p in projs]
    assert sorted(gw_ids) == [1, 2, 3, 4]
