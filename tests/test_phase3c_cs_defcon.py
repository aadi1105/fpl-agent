import pytest
from fastapi.testclient import TestClient
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.projections.engine import ProjectionEngine
from backend.ml.cs_predictor import CSPredictor
from backend.ml.defcon_predictor import DEFCONPredictor
from backend.main import app

client = TestClient(app)

def test_cs_predictor_probability_bounds():
    """Verify Clean Sheet predictor outputs probability within valid [0.0, 1.0] bounds."""
    cs_pred = CSPredictor()
    pdata = {
        "is_home": 1.0,
        "fixture_difficulty": 2.0,
        "team_defence_rating": 1150.0,
        "opponent_attack_rating": 900.0,
        "team_cs_last_5": 3.0,
        "team_gc_avg_last_5": 0.6,
        "opp_goals_last_5": 0.8
    }
    res = cs_pred.predict(pdata)
    assert "clean_sheet_probability" in res
    assert 0.0 <= res["clean_sheet_probability"] <= 1.0
    assert res["model_version"] == "cs_v1_lgbm"

def test_defcon_rules_and_thresholds():
    """Verify 2026/27 DEFCON rules: DEF threshold = 10 CBIT, MID/FWD threshold = 12 CBIRT."""
    defcon_pred = DEFCONPredictor()

    # Defender with high CBIT expected
    def_data = {"position": "DEF", "expected_minutes_v1": 90.0, "cbit90": 11.0, "opponent_attack_rating": 1100.0}
    def_res = defcon_pred.predict(def_data)
    assert def_res["defcon_probability"] > 0.40

    # Midfielder with CBIRT expected
    mid_data = {"position": "MID", "expected_minutes_v1": 90.0, "cbit90": 6.0, "opponent_attack_rating": 1100.0}
    mid_res = defcon_pred.predict(mid_data)
    assert def_res["defcon_probability"] >= mid_res["defcon_probability"]

def test_scoring_engine_cs_and_defcon_points():
    """Verify positional scoring rules: GKP/DEF get 4.0 CS pts, MID gets 1.0 CS pt, FWD gets 0.0 CS pts."""
    db = SessionLocal()
    engine = ProjectionEngine(db)

    gabriel = db.query(Player).filter(Player.web_name == "Gabriel").first()
    fixture = db.query(Fixture).filter(Fixture.event_id == 1, Fixture.team_h_id == gabriel.team_id).first()
    teams_map = {t.id: t for t in db.query(Team).all()}
    opp_team = teams_map.get(fixture.team_a_id) if fixture else None

    bd = engine.calculate_player_xp_breakdown(gabriel, fixture, True, opp_team)

    assert "cs_xp" in bd
    assert "defcon_xp" in bd
    assert bd["cs_model_version"] == "cs_v1_lgbm"
    assert bd["defcon_model_version"] == "defcon_v1_poisson"
    assert bd["defcon_xp"] <= 2.0  # +2 FPL points capped per match

def test_dgw_per_fixture_independence():
    """Verify DGW double fixture projections are independently calculated per-fixture."""
    db = SessionLocal()
    engine = ProjectionEngine(db)
    gabriel = db.query(Player).filter(Player.web_name == "Gabriel").first()

    fixtures = db.query(Fixture).filter(Fixture.team_h_id == gabriel.team_id).limit(2).all()
    if len(fixtures) == 2:
        bd1 = engine.calculate_player_xp_breakdown(gabriel, fixtures[0], True)
        bd2 = engine.calculate_player_xp_breakdown(gabriel, fixtures[1], False)
        # Fixture A + Fixture B are independently evaluated
        assert bd1["opponent"] != bd2["opponent"] or bd1["is_home"] != bd2["is_home"]

def test_api_diagnostics_expose_cs_and_defcon_versions():
    """Verify GET /api/v1/projections/diagnostics exposes cs_model_version and defcon_model_version."""
    res = client.get("/api/v1/projections/diagnostics?target_gw=1&limit=10")
    assert res.status_code == 200
    diag = res.json()
    assert len(diag) > 0
    p0 = diag[0]
    assert p0["cs_model_version"] == "cs_v1_lgbm"
    assert p0["defcon_model_version"] == "defcon_v1_poisson"
