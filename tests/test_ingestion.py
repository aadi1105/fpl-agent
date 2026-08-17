import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Team, Player, Gameweek, Fixture, ElementType
from backend.ingestion.fpl_api import FPLDataIngestion

# In-memory SQLite DB for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    yield session
    session.close()

def test_sync_teams(db_session):
    ingestion = FPLDataIngestion()
    mock_teams = [
        {"id": 1, "name": "Arsenal", "short_name": "ARS", "code": 3, "strength": 5},
        {"id": 2, "name": "Aston Villa", "short_name": "AVL", "code": 7, "strength": 4}
    ]
    count = ingestion.sync_teams(db_session, mock_teams)
    assert count == 2
    
    teams = db_session.query(Team).all()
    assert len(teams) == 2
    assert teams[0].name == "Arsenal"
    assert teams[0].short_name == "ARS"

def test_sync_gameweeks(db_session):
    ingestion = FPLDataIngestion()
    mock_events = [
        {"id": 1, "name": "Gameweek 1", "is_current": True, "finished": True},
        {"id": 2, "name": "Gameweek 2", "is_next": True, "finished": False}
    ]
    count = ingestion.sync_gameweeks(db_session, mock_events)
    assert count == 2
    
    gw1 = db_session.query(Gameweek).filter(Gameweek.id == 1).first()
    assert gw1.is_current is True
    assert gw1.finished is True

def test_sync_players(db_session):
    ingestion = FPLDataIngestion()
    # First sync teams so foreign key passes
    db_session.add(Team(id=1, name="Arsenal", short_name="ARS"))
    db_session.commit()
    
    mock_elements = [
        {
            "id": 101,
            "code": 1234,
            "web_name": "Saka",
            "first_name": "Bukayo",
            "second_name": "Saka",
            "team": 1,
            "element_type": 3, # MID
            "now_cost": 100,
            "status": "a",
            "total_points": 180,
            "expected_goals": "12.5",
            "expected_assists": "9.2"
        }
    ]
    count = ingestion.sync_players(db_session, mock_elements)
    assert count == 1
    
    player = db_session.query(Player).filter(Player.id == 101).first()
    assert player.web_name == "Saka"
    assert player.element_type == "MID"
    assert player.expected_goals == 12.5
