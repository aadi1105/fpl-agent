import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import get_db, Base
from backend.models import Team, Player, Gameweek, Fixture, ElementType, PlayerProjection
from backend.projections.engine import ProjectionEngine

TEST_DB_FILE = "test_phase1a.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
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
    session.add(saka)
    session.commit()
    
    proj_engine = ProjectionEngine(session)
    proj_engine.run_projections(start_gw=1, end_gw=4, source="internal")
    
    session.close()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.fixture
def client():
    return TestClient(app)

def test_api_returns_independent_gw0_to_gw3_diagnostics(client):
    resp = client.get("/api/v1/projections/diagnostics?target_gw=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) > 0

    saka_data = next((p for p in data if p["web_name"] == "Saka"), None)
    assert saka_data is not None

    assert saka_data["gw0_opponent"] == "IPS (H)"
    assert saka_data["gw1_opponent"] == "MCI (A)"
    assert saka_data["gw2_opponent"] == "CHE (H)"
    assert saka_data["gw3_opponent"] == "IPS (A)"

    # Regression check: gw0_xp (vs IPS Home) must NOT equal gw1_xp (vs MCI Away)
    assert saka_data["gw0_xp"] != saka_data["gw1_xp"]
    assert saka_data["gw0_xp"] > saka_data["gw1_xp"]
