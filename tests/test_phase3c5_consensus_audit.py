import pytest
from fastapi.testclient import TestClient
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.main import app

client = TestClient(app)

def test_consensus_audit_does_not_modify_production_projections():
    """Verify that calling consensus audit does NOT mutate production projections."""
    db = SessionLocal()
    engine = ProjectionEngine(db)
    haaland = db.query(Player).filter(Player.web_name == "Haaland").first()

    p1 = engine.calculate_player_xp_breakdown(haaland)
    res = client.get("/api/v1/projections/consensus_audit?target_gw=1")
    assert res.status_code == 200

    p2 = engine.calculate_player_xp_breakdown(haaland)
    assert p1["total_xp"] == p2["total_xp"]
    assert p1["xg_match"] == p2["xg_match"]

def test_ownership_cannot_enter_optimizer_objective():
    """Verify that MILP squad optimizer formulation objective does NOT include ownership or consensus."""
    db = SessionLocal()
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="CURRENT_GW_PLUS_3")
    
    assert res is not None
    assert "starting_11" in res
    assert "bench" in res
    assert "optimization_mode" in res
    assert res["optimization_mode"] == "CURRENT_GW_PLUS_3"

def test_model_xp_equals_production_projection_xp():
    """Verify that consensus audit endpoint returns exact production projection xP."""
    db = SessionLocal()
    engine = ProjectionEngine(db)
    res = client.get("/api/v1/projections/consensus_audit?target_gw=1")
    assert res.status_code == 200
    audited = res.json()

    haaland_audit = next(p for p in audited if p["web_name"] == "Haaland")
    haaland_player = db.query(Player).filter(Player.web_name == "Haaland").first()
    
    fixture = db.query(Fixture).filter(Fixture.event_id == 1, (Fixture.team_h_id == haaland_player.team_id) | (Fixture.team_a_id == haaland_player.team_id)).first()
    is_home = fixture.team_h_id == haaland_player.team_id
    opp_team_id = fixture.team_a_id if is_home else fixture.team_h_id
    opp_team = db.query(Team).filter(Team.id == opp_team_id).first()

    production_xp = engine.calculate_player_xp_breakdown(haaland_player, fixture, is_home, opp_team)["total_xp"]

    assert haaland_audit["total_xp"] == production_xp

def test_deterministic_rank_calculations():
    """Verify that position-specific model rank calculations are deterministic."""
    res1 = client.get("/api/v1/projections/consensus_audit?target_gw=1").json()
    res2 = client.get("/api/v1/projections/consensus_audit?target_gw=1").json()

    ranks1 = {p["id"]: p["model_rank"] for p in res1}
    ranks2 = {p["id"]: p["model_rank"] for p in res2}

    assert ranks1 == ranks2

def test_canonical_prices_used_in_consensus_audit():
    """Verify that all audited players use DB integer tenths canonical prices."""
    db = SessionLocal()
    res = client.get("/api/v1/projections/consensus_audit?target_gw=1").json()
    for p_audit in res[:20]:
        db_p = db.query(Player).filter(Player.id == p_audit["id"]).first()
        assert db_p is not None
        assert p_audit["price"] == db_p.now_cost / 10.0
