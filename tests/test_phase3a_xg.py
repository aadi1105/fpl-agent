import pytest
import os
import json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Player, Team, Fixture, Gameweek, ElementType
from backend.ml.xg_dataset_builder import HistoricalXGDatasetBuilder
from backend.ml.xg_predictor import XGPredictor
from backend.projections.engine import ProjectionEngine

TEST_DB_URL = "sqlite:///./test_phase3a.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create test gameweek
    gw = Gameweek(id=1, name="Gameweek 1", is_current=True)
    db.add(gw)

    # Create teams
    t1 = Team(id=1, name="Arsenal", short_name="ARS", strength_attack_home=1200, strength_defence_home=1200, strength_attack_away=1150, strength_defence_away=1150)
    t2 = Team(id=2, name="Chelsea", short_name="CHE", strength_attack_home=1000, strength_defence_home=1000, strength_attack_away=950, strength_defence_away=950)
    db.add_all([t1, t2])

    # Create fixture
    f1 = Fixture(id=1, event_id=1, team_h_id=1, team_a_id=2, team_h_difficulty=2, team_a_difficulty=4)
    db.add(f1)

    # Create players
    p1 = Player(id=1, web_name="Saka", element_type="MID", team_id=1, now_cost=100, minutes=2500, goals_scored=14, assists=10)
    p2 = Player(id=2, web_name="Haaland", element_type="FWD", team_id=1, now_cost=140, minutes=2700, goals_scored=27, assists=5)
    db.add_all([p1, p2])

    db.commit()
    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_phase3a.db"):
        try:
            os.remove("./test_phase3a.db")
        except PermissionError:
            pass

def test_xg_dataset_builder_structure():
    builder = HistoricalXGDatasetBuilder()
    df_raw = pd.DataFrame([{
        "element": 1, "name": "Saka", "position": "MID", "team": "ARS", "opponent_team": 2,
        "was_home": True, "value": 100, "gameweek": 1, "fixture": 101, "minutes": 90,
        "starts": 1, "goals_scored": 1, "expected_goals": 0.65, "threat": 60, "creativity": 45,
        "kickoff_time": "2025-08-15T19:00:00Z"
    }])
    
    res = builder.process_season("2025-26", df_raw)
    assert len(res) == 1
    assert "expected_minutes_v1" in res.columns
    assert "target_goals" in res.columns
    assert "actual_xg" in res.columns
    assert res.iloc[0]["goals_last_1"] == 0.0  # Leakage check: GW1 prior goals shifted to 0

def test_xg_predictor_inference():
    predictor = XGPredictor()
    assert predictor.is_loaded is True

    pdata = {
        "price": 10.0,
        "position": "MID",
        "expected_minutes_v1": 85.0,
        "opponent_defence_rating": 900.0,
        "team_attack_rating": 1200.0,
        "xg_last_5": 2.5,
        "goals_last_5": 3.0,
        "threat_last_10": 350.0,
        "home_away_is_home": 1.0
    }

    res = predictor.predict(pdata)
    assert "expected_goals" in res
    assert res["expected_goals"] >= 0.0
    assert res["model_version"] == "xg_v1_lgbm"
    assert res["used_fallback"] is False

def test_xg_predictor_fallback():
    predictor = XGPredictor()
    predictor.is_loaded = False  # Simulate failure mode

    pdata = {
        "price": 10.0,
        "position": "MID",
        "expected_minutes_v1": 85.0,
        "opponent_defence_rating": 900.0,
        "home_away_is_home": 1.0
    }

    res = predictor.predict(pdata)
    assert res["used_fallback"] is True
    assert res["model_version"] == "xg_baseline_v1"
    assert res["expected_goals"] > 0.0

def test_projection_engine_xg_integration(setup_db):
    db = setup_db
    engine_proj = ProjectionEngine(db, use_ml_minutes=True, use_ml_xg=True)

    player = db.query(Player).filter_by(web_name="Saka").first()
    fixture = db.query(Fixture).filter_by(id=1).first()
    opp_team = db.query(Team).filter_by(id=2).first()

    bd = engine_proj.calculate_player_xp_breakdown(player, fixture, True, opp_team)

    assert "xg_baseline" in bd
    assert "xg_ml" in bd
    assert "xg_model_version" in bd
    assert bd["xg_match"] > 0.0
    assert bd["goals_xp"] == round(bd["xg_match"] * 5.0, 2)  # Midfielder goal value = 5.0
