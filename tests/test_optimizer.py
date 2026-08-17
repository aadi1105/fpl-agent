import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Team, Player, Gameweek, Fixture, ElementType, PlayerProjection
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.projections.engine import ProjectionEngine

TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    
    teams = [Team(id=i, name=f"Team {i}", short_name=f"T{i}") for i in range(1, 21)]
    session.add_all(teams)
    
    gw1 = Gameweek(id=1, name="Gameweek 1", is_current=True)
    session.add(gw1)

    fixtures = [
        Fixture(id=i, event_id=1, team_h_id=i, team_a_id=21-i, team_h_difficulty=3, team_a_difficulty=3)
        for i in range(1, 11)
    ]
    session.add_all(fixtures)
    
    players = []
    pid = 1
    for pos, count in [("GKP", 3), ("DEF", 8), ("MID", 8), ("FWD", 5)]:
        for k in range(count):
            cost = 130 if (pos == "FWD" and k == 0) else (100 if k == 0 else 45 + k * 5)
            p = Player(
                id=pid,
                web_name=f"{pos}_{k}",
                team_id=((pid - 1) % 20) + 1,
                element_type=pos,
                now_cost=cost,
                status="a",
                minutes=900,
                total_points=80 if cost >= 100 else 30,
                expected_goals=12.0 if (pos == "FWD" and cost == 130) else 0.5,
                expected_assists=3.0
            )
            players.append(p)
            pid += 1
            
    session.add_all(players)
    session.commit()

    proj_engine = ProjectionEngine(session)
    proj_engine.run_projections(start_gw=1, end_gw=1, source="internal")
    
    yield session
    session.close()

def test_squad_optimizer_current_gw_plus_3_mode(db_session):
    optimizer = SquadOptimizer(db_session)
    result = optimizer.solve_squad_selection(mode="CURRENT_GW_PLUS_3", current_gw=1, total_budget=1000)
    
    assert result["optimization_mode"] == "CURRENT_GW_PLUS_3"
    assert result["squad_count"] == 15
    assert len(result["starting_11"]) == 11
    assert len(result["bench"]) == 4
    assert result["total_cost"] <= 1000
    assert result["captain"] is not None
    assert result["current_gw_starting_xi_xp"] > 0
    assert result["total_current_gw_xp"] > result["current_gw_starting_xi_xp"]
    assert len(result["explanations"]) > 0

def test_squad_optimizer_strong_xi_dump_bench_mode(db_session):
    optimizer = SquadOptimizer(db_session)
    result = optimizer.solve_squad_selection(mode="STRONG_XI_DUMP_BENCH", current_gw=1, total_budget=1000)
    
    assert result["optimization_mode"] == "STRONG_XI_DUMP_BENCH"
    assert result["squad_count"] == 15
    assert len(result["starting_11"]) == 11
    assert len(result["bench"]) == 4
