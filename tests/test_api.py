import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import get_db, Base
from backend.models import Team, Player, Gameweek, Fixture, ElementType, PlayerProjection
from backend.projections.engine import ProjectionEngine

TEST_DB_FILE = "test_api.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
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
    
    pid = 1
    players = []
    for pos, count in [("GKP", 3), ("DEF", 8), ("MID", 8), ("FWD", 5)]:
        for k in range(count):
            p = Player(
                id=pid,
                web_name=f"{pos}_{k}",
                team_id=((pid - 1) % 20) + 1,
                element_type=pos,
                now_cost=50 + (pid % 50),
                status="a",
                minutes=900,
                total_points=50 + pid * 2
            )
            players.append(p)
            pid += 1
            
    session.add_all(players)
    session.commit()
    
    proj_engine = ProjectionEngine(session)
    proj_engine.run_projections(start_gw=1, end_gw=1, source="internal")
    
    session.close()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

def test_list_players(client):
    resp = client.get("/api/v1/players?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10

def test_diagnostics_api(client):
    resp = client.get("/api/v1/projections/diagnostics?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 10
    assert "appearance_xp" in data[0]
    assert data[0]["arithmetic_valid"] is True

def test_optimize_squad_api_current_gw_plus_3(client):
    payload = {
        "mode": "CURRENT_GW_PLUS_3",
        "current_gw": 1,
        "total_budget": 1000,
        "max_players_per_team": 3
    }
    resp = client.post("/api/v1/optimize/squad", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["optimization_mode"] == "CURRENT_GW_PLUS_3"
    assert data["squad_count"] == 15
    assert len(data["starting_11"]) == 11
    assert len(data["bench"]) == 4
    assert data["captain"] is not None
