import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================================================
# PHASE 3N.20 — PROJECTION INTEGRITY & LANDING PAGE TESTS
# ==================================================

def test_my_team_returns_non_zero_xp(client, db_session):
    """Verify My Team returns realistic non-zero xP for individual players and starting XI total when configured."""
    from backend.user.user_squad import UserSquadManager
    mgr = UserSquadManager(db_session)
    squad_dict = mgr.get_user_squad_dict()
    if not squad_dict["is_configured"]:
        gkps = [p.id for p in db_session.query(Player).filter(Player.element_type == "GKP").limit(2).all()]
        defs = [p.id for p in db_session.query(Player).filter(Player.element_type == "DEF").limit(5).all()]
        mids = [p.id for p in db_session.query(Player).filter(Player.element_type == "MID").limit(5).all()]
        fwds = [p.id for p in db_session.query(Player).filter(Player.element_type == "FWD").limit(3).all()]
        all_15 = gkps + defs + mids + fwds
        starters = [gkps[0]] + defs[:3] + mids[:4] + fwds[:3]
        mgr.update_user_squad(
            player_ids=all_15,
            bank=0,
            free_transfers=1,
            active_chip=None,
            captain_id=fwds[0],
            vice_captain_id=mids[0],
            starter_ids=starters
        )

    # Fetch configured user squad
    res = client.get("/api/v1/user-squad")
    assert res.status_code == 200
    sq = res.json()

    assert sq["is_configured"] is True
    assert "starting_xi_xp" in sq
    assert sq["starting_xi_xp"] > 20.0, f"Expected starting XI xP > 20.0, got {sq['starting_xi_xp']}"

    assert "starting_11" in sq
    starters = sq["starting_11"]
    assert len(starters) == 11

    # Check individual player xP is non-zero for starters
    for p in starters:
        assert p["gw_xp"] > 0.0, f"Expected player {p['web_name']} xP > 0, got {p['gw_xp']}"
        assert p["total_xp"] == p["gw_xp"]
        assert p["expected_points_gw"] == p["gw_xp"]

def test_model_audit_returns_real_probabilities_and_xmins(client):
    """Verify consensus audit endpoint returns real expected-minutes model outputs (no blanket 0m or 100% P(Start))."""
    res = client.get("/api/v1/projections/consensus_audit?target_gw=2")
    assert res.status_code == 200
    audited = res.json()
    assert len(audited) > 0

    # Key players check
    key_names = ["Haaland", "Fernandes", "Isak", "Palmer", "Saka", "Mbeumo", "Pedro"]
    found = [p for p in audited if any(k in p["web_name"] for k in key_names)]
    assert len(found) > 0

    for p in found:
        assert p["xMins"] > 0.0, f"Expected xMins > 0 for {p['web_name']}, got {p['xMins']}"
        assert 0.0 < p["p_start"] <= 1.0, f"Expected p_start between 0 and 1 for {p['web_name']}, got {p['p_start']}"
        assert 0.0 < p["p_60_plus"] <= 1.0, f"Expected p_60_plus between 0 and 1 for {p['web_name']}, got {p['p_60_plus']}"
        assert 0.0 <= p["p_zero"] < 1.0, f"Expected p_zero between 0 and 1 for {p['web_name']}, got {p['p_zero']}"
        assert p["total_xp"] > 0.0, f"Expected total_xp > 0 for {p['web_name']}, got {p['total_xp']}"

def test_my_team_is_default_landing_page(client):
    """Verify My Team Command Center is set as the default active landing page in HTML."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert '<div id="tab-my-team" class="tab-content" style="display:block;">' in html
    assert '<button class="nav-btn active" onclick="switchMainTab(\'my-team\')">MY TEAM COMMAND CENTER</button>' in html
