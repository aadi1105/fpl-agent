import pytest
import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.ml.minutes_predictor import MinutesPredictor
from backend.projections.engine import ProjectionEngine

client = TestClient(app)

def test_minutes_predictor_schema():
    predictor = MinutesPredictor()
    dummy_pdata = {
        'price': 14.0,
        'fixture_difficulty': 2,
        'team_attack_rating': 1200.0,
        'team_defence_rating': 1100.0,
        'opponent_attack_rating': 900.0,
        'opponent_defence_rating': 950.0,
        'home_away_is_home': 1.0,
        'minutes_last_1': 90.0,
        'minutes_last_3': 270.0,
        'minutes_last_5': 450.0,
        'minutes_last_10': 900.0,
        'starts_last_1': 1.0,
        'starts_last_3': 3.0,
        'starts_last_5': 5.0,
        'starts_last_10': 10.0,
        'appearances_last_5': 5.0,
        'bench_appearances_last_5': 0.0,
        'unused_substitute_last_5': 0.0,
        'average_minutes_last_5': 90.0,
        'average_minutes_last_10': 90.0,
        'days_since_last_match': 7.0,
        'matches_in_previous_14_days': 2.0,
        'matches_in_previous_21_days': 3.0,
        'fixture_congestion': 0.0,
        'pos_DEF': 0.0,
        'pos_MID': 0.0,
        'pos_FWD': 1.0
    }

    res = predictor.predict(dummy_pdata)

    assert "expected_minutes" in res
    assert "p_start" in res
    assert "p_60_plus" in res
    assert "p_zero" in res
    assert "model_version" in res
    assert "used_fallback" in res

    assert 0.0 <= res["p_start"] <= 1.0
    assert 0.0 <= res["p_60_plus"] <= 1.0
    assert 0.0 <= res["p_zero"] <= 1.0
    assert 0.0 <= res["expected_minutes"] <= 180.0
    assert res["model_version"] == "expected_minutes_v1"
    assert res["used_fallback"] is False

def test_minutes_predictor_fallback_mode():
    # Pass empty dir to force fallback trigger
    predictor = MinutesPredictor(model_dir="non_existent_dir_123")
    res = predictor.predict({"average_minutes_last_5": 75.0, "starts_last_5": 4.0})

    assert res["used_fallback"] is True
    assert res["model_version"] == "expected_minutes_baseline_v1"
    assert res["expected_minutes"] == 75.0
    assert res["p_start"] == 0.8

def test_engine_integration_no_double_counting():
    db = SessionLocal()
    try:
        engine = ProjectionEngine(db, use_ml_minutes=True)
        player = db.query(Player).first()
        if player:
            bd = engine.calculate_player_xp_breakdown(player)
            
            assert "expected_minutes_baseline" in bd
            assert "expected_minutes_ml" in bd
            assert "model_version" in bd
            assert "p_start" in bd
            assert "p_60_plus" in bd
            assert "p_zero" in bd

            # Confirm total_xp arithmetic equality with components (no double counting of minutes)
            comp_sum = round(
                bd["appearance_xp"] + bd["goals_xp"] + bd["assists_xp"] +
                bd["cs_xp"] + bd["defcon_xp"] + bd["saves_xp"] +
                bd["bonus_xp"] + bd["cards_xp"], 2
            )
            assert abs(bd["total_xp"] - max(0.0, comp_sum)) < 0.05
    finally:
        db.close()

def test_diagnostics_endpoint_includes_ml_minutes():
    response = client.get("/api/v1/projections/diagnostics?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        row = data[0]
        assert "expected_minutes_baseline" in row
        assert "expected_minutes_ml" in row
        assert "model_version" in row
        assert "p_start" in row
        assert "p_60_plus" in row
        assert "p_zero" in row
        assert "used_fallback" in row
