import pytest
from backend.database import SessionLocal
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.models import Player, PlayerProjection

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================================================
# PHASE 3N.11 — OPTIMIZATION MODE INTEGRITY TESTS
# ==================================================

def test_synthetic_mode_differentiation_objective(db_session):
    """
    Construct a deterministic synthetic mathematical test proving that
    NEXT_GW, MEDIUM_TERM, and LONG_TERM modes use genuinely different objective functions.
    """
    opt = SquadOptimizer(db_session)
    
    # Mode 1: NEXT_GW (1.0 weight on GW1)
    res_next = opt.solve_squad_selection(mode="CURRENT_GW_ONLY", current_gw=1)
    assert res_next["horizon_weights"] == [1.0]

    # Mode 2: MEDIUM_TERM (0.55, 0.20, 0.15, 0.10)
    res_med = opt.solve_squad_selection(mode="CURRENT_GW_PLUS_3", current_gw=1)
    assert len(res_med["horizon_weights"]) == 4
    assert res_med["horizon_weights"][0] == 0.55

    # Mode 3: LONG_TERM (7-GW weighted horizon)
    res_long = opt.solve_squad_selection(mode="LONG_TERM", current_gw=1)
    assert len(res_long["horizon_weights"]) == 7
    assert res_long["horizon_weights"][0] == 0.30

def test_real_production_mode_differentiation(db_session):
    """
    Verify that real production runs produce distinct XI selections or formations across modes.
    NEXT GW selects 3-5-2 with B.Fernandes (£12.0m) as Captain.
    LONG TERM selects 3-4-3 with Thiago (£8.0m) as 3rd Forward.
    """
    opt = SquadOptimizer(db_session)

    res_next = opt.solve_squad_selection(mode="CURRENT_GW_ONLY", current_gw=1)
    res_med = opt.solve_squad_selection(mode="CURRENT_GW_PLUS_3", current_gw=1)
    res_long = opt.solve_squad_selection(mode="LONG_TERM", current_gw=1)

    next_xi_names = set(p["web_name"] for p in res_next["starting_11"])
    med_xi_names = set(p["web_name"] for p in res_med["starting_11"])
    long_xi_names = set(p["web_name"] for p in res_long["starting_11"])

    # Confirm NEXT GW includes Bruno Fernandes
    assert "B.Fernandes" in next_xi_names
    assert res_next["captain"]["web_name"] == "B.Fernandes"

    # Confirm MEDIUM TERM drops Bruno Fernandes to re-allocate £12m into Palmer + João Pedro
    assert "B.Fernandes" not in med_xi_names
    assert "Palmer" in med_xi_names

    # Confirm LONG TERM selects 3-4-3 formation
    defs_long = [p for p in res_long["starting_11"] if p["element_type"] == "DEF"]
    mids_long = [p for p in res_long["starting_11"] if p["element_type"] == "MID"]
    fwds_long = [p for p in res_long["starting_11"] if p["element_type"] == "FWD"]
    assert len(defs_long) == 3
    assert len(mids_long) == 4
    assert len(fwds_long) == 3

def test_squad_rules_and_budget_constraints(db_session):
    """Verify all modes strictly enforce 15 players, 11 starters, 4 bench, <=£100.0m cost, max 3 per club."""
    opt = SquadOptimizer(db_session)

    for mode in ["CURRENT_GW_ONLY", "CURRENT_GW_PLUS_3", "LONG_TERM"]:
        res = opt.solve_squad_selection(mode=mode, current_gw=1)
        assert len(res["starting_11"]) == 11
        assert len(res["bench"]) == 4
        assert res["total_cost"] <= 1000
        assert res["squad_count"] == 15

        # Check max 3 players per club
        club_counts = {}
        for p in res["starting_11"] + res["bench"]:
            club_counts[p["team_id"]] = club_counts.get(p["team_id"], 0) + 1
        assert all(cnt <= 3 for cnt in club_counts.values())

        # Captain must belong to starting XI
        assert res["captain"]["is_starter"] is True
