import pytest
import os
import json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import Player, Team, Fixture, Gameweek, ElementType
from backend.ml.xa_dataset_builder import HistoricalXADatasetBuilder
from backend.ml.xa_predictor import XAPredictor
from backend.projections.engine import ProjectionEngine

TEST_DB_URL = "sqlite:///./test_phase3b.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    gw = Gameweek(id=1, name="Gameweek 1", is_current=True)
    db.add(gw)

    t1 = Team(id=1, name="Arsenal", short_name="ARS", strength_attack_home=1200, strength_defence_home=1200, strength_attack_away=1150, strength_defence_away=1150)
    t2 = Team(id=2, name="Chelsea", short_name="CHE", strength_attack_home=1000, strength_defence_home=1000, strength_attack_away=950, strength_defence_away=950)
    db.add_all([t1, t2])

    f1 = Fixture(id=1, event_id=1, team_h_id=1, team_a_id=2, team_h_difficulty=2, team_a_difficulty=4)
    db.add(f1)

    p1 = Player(id=1, web_name="Palmer", element_type="MID", team_id=1, now_cost=105, minutes=2600, goals_scored=15, assists=12)
    p2 = Player(id=2, web_name="Alexander-Arnold", element_type="DEF", team_id=1, now_cost=75, minutes=2400, goals_scored=2, assists=10)
    db.add_all([p1, p2])

    db.commit()
    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_phase3b.db"):
        try:
            os.remove("./test_phase3b.db")
        except PermissionError:
            pass

def test_xa_dataset_builder_structure():
    builder = HistoricalXADatasetBuilder()
    df_raw = pd.DataFrame([{
        "element": 1, "name": "Palmer", "position": "MID", "team": "ARS", "opponent_team": 2,
        "was_home": True, "value": 105, "gameweek": 1, "fixture": 101, "minutes": 90,
        "starts": 1, "goals_scored": 1, "assists": 1, "expected_goals": 0.45, "expected_assists": 0.35,
        "creativity": 60, "threat": 45, "kickoff_time": "2025-08-15T19:00:00Z"
    }])

    res = builder.process_season("2025-26", df_raw)
    assert len(res) == 1
    assert "expected_minutes_v1" in res.columns
    assert "xg_v1_lgbm_pred" in res.columns
    assert "target_assists" in res.columns
    assert "actual_xa" in res.columns
    assert res.iloc[0]["assists_last_1"] == 0.0  # Leakage check: GW1 prior assists shifted to 0

def test_xa_predictor_inference():
    predictor = XAPredictor()
    assert predictor.is_loaded is True

    pdata = {
        "price": 10.5,
        "position": "MID",
        "expected_minutes_v1": 85.0,
        "opponent_defence_rating": 900.0,
        "team_attack_rating": 1200.0,
        "xa_last_5": 1.8,
        "assists_last_5": 2.0,
        "creativity_last_10": 450.0,
        "xg_v1_lgbm_pred": 0.45,
        "home_away_is_home": 1.0
    }

    res = predictor.predict(pdata)
    assert "expected_assists" in res
    assert res["expected_assists"] >= 0.0
    assert res["model_version"] in ["xa_v1_lgbm", "xa_v2"]
    assert res["used_fallback"] is False

def test_xa_predictor_fallback():
    predictor = XAPredictor()
    predictor.is_loaded = False

    pdata = {
        "price": 10.5,
        "position": "MID",
        "expected_minutes_v1": 85.0,
        "opponent_defence_rating": 900.0,
        "home_away_is_home": 1.0
    }

    res = predictor.predict(pdata)
    assert res["used_fallback"] is True
    assert res["model_version"] == "xa_baseline_v1"
    assert res["expected_assists"] > 0.0

def test_projection_engine_xa_integration(setup_db):
    db = setup_db
    engine_proj = ProjectionEngine(db, use_ml_minutes=True, use_ml_xg=True, use_ml_xa=True)

    player = db.query(Player).filter_by(web_name="Palmer").first()
    fixture = db.query(Fixture).filter_by(id=1).first()
    opp_team = db.query(Team).filter_by(id=2).first()

    bd = engine_proj.calculate_player_xp_breakdown(player, fixture, True, opp_team)

    assert "xa_baseline" in bd
    assert "xa_ml" in bd
    assert "xa_model_version" in bd
    assert bd["xa_match"] > 0.0
    assert bd["assists_xp"] == round(bd["xa_match"] * 3.0, 2)  # Assist value = 3.0
