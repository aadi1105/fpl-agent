import pytest
import os
import json
import pickle
from backend.database import SessionLocal
from backend.models import Player, Fixture, Team
from backend.projections.engine import ProjectionEngine

def test_phase3h_calibration_artifacts_exist():
    cs_path = os.path.join("backend", "ml", "models", "cs_calibration_v1.pkl")
    meta_path = os.path.join("backend", "ml", "models", "expected_xp_calibrated_v1.json")
    
    assert os.path.exists(cs_path), "CS calibration model artifact missing."
    assert os.path.exists(meta_path), "Expected xP calibration metadata missing."

def test_phase3h_calibrated_projection_values():
    db = SessionLocal()
    try:
        engine = ProjectionEngine(db=db)
        haaland = db.query(Player).filter(Player.web_name == "Haaland").first()
        assert haaland is not None, "Haaland missing in DB."

        fix = db.query(Fixture).filter(
            ((Fixture.team_h_id == haaland.team_id) | (Fixture.team_a_id == haaland.team_id)),
            Fixture.event_id == 1
        ).first()
        is_h = (fix.team_h_id == haaland.team_id)
        opp_i = fix.team_a_id if is_h else fix.team_h_id
        opp_t = db.query(Team).filter(Team.id == opp_i).first()

        bd = engine.calculate_player_xp_breakdown(haaland, fixture=fix, is_home=is_h, opp_team=opp_t)

        assert "raw_xp" in bd, "raw_xp missing in breakdown."
        assert "calibrated_xp" in bd, "calibrated_xp missing in breakdown."
        assert "adjustment" in bd, "adjustment missing in breakdown."
        assert bd["calibrated_xp"] > bd["raw_xp"], "Haaland calibrated_xp should exceed raw_xp."
        assert bd["total_xp"] == bd["calibrated_xp"], "total_xp should match calibrated_xp."
    finally:
        db.close()

def test_phase3h_defender_calibration_adjustment():
    db = SessionLocal()
    try:
        engine = ProjectionEngine(db=db)
        calafiori = db.query(Player).filter(Player.web_name == "Calafiori").first()
        assert calafiori is not None, "Calafiori missing in DB."

        fix = db.query(Fixture).filter(
            ((Fixture.team_h_id == calafiori.team_id) | (Fixture.team_a_id == calafiori.team_id)),
            Fixture.event_id == 1
        ).first()
        is_h = (fix.team_h_id == calafiori.team_id)
        opp_i = fix.team_a_id if is_h else fix.team_h_id
        opp_t = db.query(Team).filter(Team.id == opp_i).first()

        bd = engine.calculate_player_xp_breakdown(calafiori, fixture=fix, is_home=is_h, opp_team=opp_t)

        assert bd["calibrated_xp"] < bd["raw_xp"], "Calafiori defender raw xP should be scaled down."
        assert bd["adjustment"] < 0, "Defender adjustment should be negative."
    finally:
        db.close()
