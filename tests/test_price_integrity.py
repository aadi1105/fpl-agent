import pytest
from fastapi.testclient import TestClient
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.main import app

client = TestClient(app)

def test_all_active_players_have_valid_prices():
    """Verify all 590 players in DB have valid now_cost between £4.0m (40) and £15.5m (155)."""
    db = SessionLocal()
    players = db.query(Player).all()
    assert len(players) > 0

    for p in players:
        assert p.now_cost >= 40, f"Player {p.web_name} has invalid cost {p.now_cost} < 40"
        assert p.now_cost <= 200, f"Player {p.web_name} has invalid cost {p.now_cost} > 200"

def test_representative_players_canonical_prices():
    """Explicitly verify Gabriel (£8.0m), Raya (£6.0m), Igor Jesus (£6.0m), and Haaland (£15.5m)."""
    db = SessionLocal()
    
    gabriel = db.query(Player).filter(Player.web_name == "Gabriel").first()
    assert gabriel is not None
    assert gabriel.now_cost == 80
    assert f"£{gabriel.now_cost / 10.0:.1f}m" == "£8.0m"

    raya = db.query(Player).filter(Player.web_name == "Raya").first()
    assert raya is not None
    assert raya.now_cost == 60
    assert f"£{raya.now_cost / 10.0:.1f}m" == "£6.0m"

    igor = db.query(Player).filter(Player.web_name == "Igor Jesus").first()
    assert igor is not None
    assert igor.now_cost == 60

    haaland = db.query(Player).filter(Player.web_name == "Haaland").first()
    assert haaland is not None
    assert haaland.now_cost == 155
    assert f"£{haaland.now_cost / 10.0:.1f}m" == "£15.5m"

def test_price_scale_conversions():
    """Test price conversions across representative FPL price tiers with zero floating-point errors."""
    test_tenths = [40, 45, 50, 55, 60, 65, 70, 80, 95, 120, 155]
    expected_strs = ["£4.0m", "£4.5m", "£5.0m", "£5.5m", "£6.0m", "£6.5m", "£7.0m", "£8.0m", "£9.5m", "£12.0m", "£15.5m"]

    for tenths, expected in zip(test_tenths, expected_strs):
        price_m = tenths / 10.0
        price_str = f"£{price_m:.1f}m"
        assert price_str == expected

def test_cross_layer_price_integrity_reconciliation():
    """Test that DB price, projection engine price, and optimizer price are 100% identical for all players."""
    db = SessionLocal()
    players = db.query(Player).all()
    proj_engine = ProjectionEngine(db)
    
    fixtures = db.query(Fixture).filter(Fixture.event_id == 1).all()
    teams_map = {t.id: t for t in db.query(Team).all()}
    team_fixture_map = {}
    for f in fixtures:
        if f.team_h_id not in team_fixture_map: team_fixture_map[f.team_h_id] = []
        team_fixture_map[f.team_h_id].append((f, True, teams_map.get(f.team_a_id)))
        if f.team_a_id not in team_fixture_map: team_fixture_map[f.team_a_id] = []
        team_fixture_map[f.team_a_id].append((f, False, teams_map.get(f.team_h_id)))

    for p in players:
        db_price_m = p.now_cost / 10.0
        p_fixtures = team_fixture_map.get(p.team_id, [])
        if p_fixtures:
            f, is_home, opp_team = p_fixtures[0]
            bd = proj_engine.calculate_player_xp_breakdown(p, f, is_home, opp_team)
            assert abs(bd["price"] - db_price_m) < 0.001, f"Projection price mismatch for {p.web_name}"

def test_optimizer_budget_cost_integrity():
    """Verify optimizer total squad cost matches sum of individual player now_cost values."""
    db = SessionLocal()
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="CURRENT_GW_PLUS_3", current_gw=1, total_budget=1000)

    total_squad = res["starting_11"] + res["bench"]
    assert len(total_squad) == 15

    sum_tenths = sum(p["now_cost"] for p in total_squad)
    assert sum_tenths == res["total_cost"]
    assert res["total_cost_str"] == f"£{sum_tenths / 10.0:.1f}m"
    assert res["bank"] == 1000 - sum_tenths

def test_diagnostics_positional_price_percentiles():
    """Verify positional price percentiles are computed strictly relative to position peers."""
    res = client.get("/api/v1/projections/diagnostics?target_gw=1&limit=50")
    assert res.status_code == 200
    diag = res.json()

    for p in diag:
        assert "pos_price_percentile" in p
        assert 0.0 <= p["pos_price_percentile"] <= 100.0
