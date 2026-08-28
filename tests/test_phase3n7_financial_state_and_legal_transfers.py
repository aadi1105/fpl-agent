import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, UserSquad, UserPick
from backend.user.user_squad import UserSquadManager
from backend.optimizer.squad_optimizer import SquadOptimizer

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_bank_zero_persistence_and_reload(client, db_session):
    """Verify bank = 0 (£0.0m) persists across save, reload, and comparison engine."""
    all_players = db_session.query(Player).limit(100).all()
    gkps = [p.id for p in all_players if p.element_type == 'GKP'][:2]
    defs = [p.id for p in all_players if p.element_type == 'DEF'][:5]
    mids = [p.id for p in all_players if p.element_type == 'MID'][:5]
    fwds = [p.id for p in all_players if p.element_type == 'FWD'][:3]
    squad_ids = gkps + defs + mids + fwds

    payload = {
        "player_ids": squad_ids,
        "bank": 0,
        "free_transfers": 1,
        "active_chip": None
    }
    res = client.post("/api/v1/user-squad", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["bank"] == 0
    assert data["bank_str"] == "£0.0m"

    # Reload via GET
    get_res = client.get("/api/v1/user-squad")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["bank"] == 0
    assert get_data["bank_str"] == "£0.0m"

def test_unaffordable_transfer_rejected_with_zero_bank(db_session):
    """Verify Shaw (£4.5m) -> Guéhi (£6.0m) requiring £1.5m is STRICTLY REJECTED when bank is £0.0m."""
    mgr = UserSquadManager(db_session)
    squad = mgr.get_or_create_user_squad()
    squad.bank = 0  # £0.0m
    squad.free_transfers = 1
    db_session.commit()

    opt = SquadOptimizer(db_session)
    opt_res = opt.solve_squad_selection(mode="MEDIUM_TERM", current_gw=1)
    comp = mgr.compare_with_optimal_squad(optimal_result=opt_res, current_gw=1)

    assert comp["my_squad_bank_str"] == "£0.0m"
    rec = comp.get("recommended_transfer")

    if rec:
        sell_cost = int(float(rec["sell"]["now_cost_str"].replace("£","").replace("m","")) * 10)
        buy_cost = int(float(rec["buy"]["now_cost_str"].replace("£","").replace("m","")) * 10)
        diff = buy_cost - sell_cost
        assert diff <= 0, f"Unaffordable transfer recommended! Cost difference £{diff/10.0:.1f}m exceeds £0.0m bank!"
        assert rec["is_financially_legal"] is True

def test_actionable_vs_theoretical_separation(db_session):
    """Verify returned comparison separates actionable 1-FT transfer from theoretical unconstrained optimal squad."""
    mgr = UserSquadManager(db_session)
    opt = SquadOptimizer(db_session)
    opt_res = opt.solve_squad_selection(mode="MEDIUM_TERM", current_gw=1)
    comp = mgr.compare_with_optimal_squad(optimal_result=opt_res, current_gw=1)

    assert "actionable_1ft_recommendation" in comp
    assert "transfers_out" in comp
    assert "transfers_in" in comp
    assert "optimal_squad_starting_xp" in comp
