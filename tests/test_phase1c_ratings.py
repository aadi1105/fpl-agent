import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Team, Player, Gameweek, Fixture, ElementType, PlayerProjection
from backend.projections.team_ratings import TeamRatingCalculator
from backend.projections.engine import ProjectionEngine

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    
    # 4 teams with distinct strengths:
    # Team 1 (Elite Attack & Elite Defence): Man City / Arsenal style
    # Team 2 (Weak Attack & Weak Defence): Ipswich style
    # Team 3 (Average)
    # Team 4 (Missing ratings / unpopulated)
    t1 = Team(id=1, name="Elite FC", short_name="ELI", strength_attack_home=1400, strength_defence_home=1500, strength_attack_away=1350, strength_defence_away=1450)
    t2 = Team(id=2, name="Weak FC", short_name="WEA", strength_attack_home=750, strength_defence_home=700, strength_attack_away=700, strength_defence_away=650)
    t3 = Team(id=3, name="Average FC", short_name="AVG", strength_attack_home=1000, strength_defence_home=1000, strength_attack_away=950, strength_defence_away=950)
    t4 = Team(id=4, name="Unknown FC", short_name="UNK", strength_attack_home=0, strength_defence_home=0, strength_attack_away=0, strength_defence_away=0)
    session.add_all([t1, t2, t3, t4])
    
    gw1 = Gameweek(id=1, name="Gameweek 1", is_current=True)
    session.add(gw1)

    # Fixtures:
    # f1: Player in Team 3 (AVG) playing against Team 2 (Weak Def)
    # f2: Player in Team 3 (AVG) playing against Team 1 (Elite Def)
    f1 = Fixture(id=1, event_id=1, team_h_id=3, team_a_id=2, team_h_difficulty=2, team_a_difficulty=5)
    f2 = Fixture(id=2, event_id=1, team_h_id=3, team_a_id=1, team_h_difficulty=5, team_a_difficulty=2)
    session.add_all([f1, f2])
    
    attacker = Player(
        id=1, web_name="Attacker", team_id=3, element_type=ElementType.MID.value,
        now_cost=80, status="a", minutes=900, total_points=80,
        expected_goals=5.0, expected_assists=3.0, bps=200
    )
    defender = Player(
        id=2, web_name="Defender", team_id=3, element_type=ElementType.DEF.value,
        now_cost=55, status="a", minutes=900, total_points=50,
        expected_goals=1.0, expected_assists=0.5, defensive_contributions=60, bps=150
    )
    session.add_all([attacker, defender])
    session.commit()
    
    yield session
    session.close()

def test_team_ratings_non_zero_and_sensible_bounds(db_session):
    calc = TeamRatingCalculator(db_session)
    ratings = calc.calculate_and_update_team_ratings()
    
    for t_id, r in ratings.items():
        assert r["att_h"] > 0
        assert r["att_a"] > 0
        assert r["def_h"] > 0
        assert r["def_a"] > 0
        assert 600.0 <= r["att_h"] <= 1600.0
        assert 600.0 <= r["def_h"] <= 1600.0

def test_missing_data_uses_baseline_1000_not_500_bug(db_session):
    unk_team = db_session.query(Team).filter_by(id=4).first()
    engine = ProjectionEngine(db_session)
    attacker = db_session.query(Player).filter_by(id=1).first()
    f1 = db_session.query(Fixture).filter_by(id=1).first()

    bd = engine.calculate_player_xp_breakdown(attacker, f1, True, unk_team)
    
    # Missing data opponent rating must default to 1000.0, NOT 500.0
    assert bd["opp_defence_rating"] == 1000.0
    assert bd["fixture_attack_modifier"] <= 1.10  # Home factor 1.05, no 2.10x bug!

def test_stronger_opponent_defence_reduces_attacking_projection(db_session):
    engine = ProjectionEngine(db_session)
    attacker = db_session.query(Player).filter_by(id=1).first()
    
    t_weak_def = db_session.query(Team).filter_by(id=2).first() # Def Away 650
    t_elite_def = db_session.query(Team).filter_by(id=1).first() # Def Away 1450

    f1 = db_session.query(Fixture).filter_by(id=1).first()

    bd_vs_weak = engine.calculate_player_xp_breakdown(attacker, f1, True, t_weak_def)
    bd_vs_elite = engine.calculate_player_xp_breakdown(attacker, f1, True, t_elite_def)

    assert bd_vs_weak["opp_defence_rating"] < bd_vs_elite["opp_defence_rating"]
    assert bd_vs_weak["fixture_attack_modifier"] > bd_vs_elite["fixture_attack_modifier"]
    assert bd_vs_weak["xg_match"] > bd_vs_elite["xg_match"]
    assert bd_vs_weak["goals_xp"] > bd_vs_elite["goals_xp"]

def test_stronger_opponent_attack_reduces_cleansheet_probability(db_session):
    engine = ProjectionEngine(db_session)
    defender = db_session.query(Player).filter_by(id=2).first()

    t_weak_att = db_session.query(Team).filter_by(id=2).first() # Att Away 700
    t_elite_att = db_session.query(Team).filter_by(id=1).first() # Att Away 1350

    f1 = db_session.query(Fixture).filter_by(id=1).first()

    bd_vs_weak_att = engine.calculate_player_xp_breakdown(defender, f1, True, t_weak_att)
    bd_vs_elite_att = engine.calculate_player_xp_breakdown(defender, f1, True, t_elite_att)

    assert bd_vs_weak_att["cs_prob"] > bd_vs_elite_att["cs_prob"]
    assert bd_vs_weak_att["cs_xp"] > bd_vs_elite_att["cs_xp"]

def test_home_away_effects_work_correctly(db_session):
    engine = ProjectionEngine(db_session)
    attacker = db_session.query(Player).filter_by(id=1).first()
    t_avg = db_session.query(Team).filter_by(id=3).first()
    f1 = db_session.query(Fixture).filter_by(id=1).first()

    bd_home = engine.calculate_player_xp_breakdown(attacker, f1, True, t_avg)
    bd_away = engine.calculate_player_xp_breakdown(attacker, f1, False, t_avg)

    assert bd_home["fixture_attack_modifier"] > bd_away["fixture_attack_modifier"]
    assert bd_home["xg_match"] > bd_away["xg_match"]
