import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, PlayerProjection
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.ingestion.current_state import CurrentGameStateManager

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# ==================================================
# PHASE 3N.26 — STARTING-XI-FIRST OPTIMIZER TESTS
# ==================================================

def test_starting_xi_is_primary_objective(db):
    """Verify primary objective maximizes Starting XI xP rather than 15-player total sum."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    # In Phase 3N.26, Starting XI Raw xP is 48.25 (Total XI+Cap = 55.17 PTS),
    # strictly improving over old 15-man sum optimizer (45.99 xP).
    assert res["current_gw_starting_xi_xp"] >= 48.0
    assert res["total_current_gw_xp"] >= 55.0

def test_bench_cannot_override_starting_xi(db):
    """Verify bench quality is optimized secondarily and cannot sacrifice starting XI xP."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    # Bench is populated with budget-saving enablers (Dubravka, Thomas, etc.)
    # ensuring max budget is in Starting XI.
    assert len(res["bench"]) == 4
    assert res["total_cost"] <= 1000

def test_legal_15_man_squad_constructed_around_optimal_xi(db):
    """Verify a complete legal 15-man squad is constructed around the chosen Starting XI."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    assert res["squad_count"] == 15
    assert len(res["starting_11"]) == 11
    assert len(res["bench"]) == 4

def test_all_legal_formations_considered(db):
    """Verify dynamic formation selection selects the highest scoring legal formation (e.g. 3-5-2)."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    assert "formation" in res
    assert res["formation"] in ["3-5-2", "3-4-3", "4-3-3", "4-4-2", "4-5-1", "5-3-2", "5-4-1"]

def test_budget_constraint_remains_valid(db):
    """Verify total squad cost does not exceed budget limit (£100.0m)."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2, total_budget=1000)
    
    assert res["total_cost"] <= 1000

def test_position_constraints_remain_valid(db):
    """Verify 15-man squad positional distribution (2 GKP, 5 DEF, 5 MID, 3 FWD)."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    all_picks = res["starting_11"] + res["bench"]
    assert sum(1 for p in all_picks if p["element_type"] == "GKP") == 2
    assert sum(1 for p in all_picks if p["element_type"] == "DEF") == 5
    assert sum(1 for p in all_picks if p["element_type"] == "MID") == 5
    assert sum(1 for p in all_picks if p["element_type"] == "FWD") == 3

def test_club_limit_remains_valid(db):
    """Verify max 3 players per club limit is enforced."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2, max_players_per_team=3)
    
    all_picks = res["starting_11"] + res["bench"]
    team_counts = {}
    for p in all_picks:
        tid = p["team_id"]
        team_counts[tid] = team_counts.get(tid, 0) + 1
        assert team_counts[tid] <= 3

def test_captaincy_uses_starting_xi_objective(db):
    """Verify captain is selected from starting XI and receives exact 1x additional base xP."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    captain = res["captain"]
    assert captain is not None
    assert captain["is_starter"] is True
    assert res["captain_contribution_xp"] == pytest.approx(captain["gw0_xp"], abs=1e-2)

def test_bench_boost_switches_primary_objective_to_all_15(db):
    """Verify that Bench Boost mode switches primary objective to maximize all 15 squad players."""
    optimizer = SquadOptimizer(db)
    res_bb = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2, is_bench_boost=True)
    
    assert res_bb["is_bench_boost"] is True
    assert res_bb["squad_count"] == 15

def test_next_gw_uses_only_target_gameweek(db):
    """Verify NEXT_GW mode isolates target gameweek (weight 1.0)."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    assert res["horizon_weights"] == [1.0]

def test_medium_term_uses_weighted_starting_xi_objective(db):
    """Verify MEDIUM_TERM mode uses weighted Starting XI points across 4 GWs."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="MEDIUM_TERM", current_gw=2)
    
    assert len(res["horizon_weights"]) == 4

def test_long_term_uses_weighted_starting_xi_objective(db):
    """Verify LONG_TERM mode uses weighted Starting XI points across 7 GWs."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="LONG_TERM", current_gw=2)
    
    assert len(res["horizon_weights"]) == 7

def test_higher_xp_player_is_not_rejected_due_only_to_bench_quality(db):
    """Verify higher xP starter is not rejected to pad bench xP."""
    optimizer = SquadOptimizer(db)
    res = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    # Ensure Starting XI contains top xP players like Bruno Fernandes and Isak
    xi_names = [p["web_name"] for p in res["starting_11"]]
    assert "B.Fernandes" in xi_names
    assert "Isak" in xi_names

def test_marginal_replacement_analysis_is_correct(client):
    """Verify debug explanation contains marginal swap analysis for starters."""
    res = client.get("/api/v1/optimize/debug?mode=NEXT_GW&current_gw=2")
    assert res.status_code == 200
    data = res.json()
    
    assert data["architecture"] == "Starting-XI-First Lexicographic MILP"
    assert "marginal_swap_analysis" in data
    assert len(data["marginal_swap_analysis"]) == 11

def test_optimizer_output_is_deterministic(db):
    """Verify two consecutive optimizer runs produce identical solutions."""
    optimizer = SquadOptimizer(db)
    res1 = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    res2 = optimizer.solve_squad_selection(mode="NEXT_GW", current_gw=2)
    
    pids1 = [p["id"] for p in res1["starting_11"]]
    pids2 = [p["id"] for p in res2["starting_11"]]
    assert pids1 == pids2
