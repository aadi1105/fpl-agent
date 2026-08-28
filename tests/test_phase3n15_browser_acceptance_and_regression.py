import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Player, PlayerProjection

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
# PHASE 3N.15 — PRODUCTION REGRESSION & BROWSER ACCEPTANCE TESTS
# ==================================================

def test_fresh_browser_load_and_diagnostics_rendered(client):
    """Verify GET /api/v1/projections/diagnostics returns 200 with valid GW2+ projections."""
    res = client.get("/api/v1/projections/diagnostics?mode=CURRENT_GW_PLUS_3&limit=50")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
    p = data[0]
    assert "web_name" in p
    assert "position" in p
    assert "weighted_xp" in p
    assert p["weighted_xp"] > 0.0

def test_optimizer_job_produces_non_empty_xi_and_score(client):
    """Verify optimizer job flow completes and returns 11 starters, 4 bench, and valid score."""
    res = client.post("/api/v1/optimize/job", json={
        "mode": "CURRENT_GW_PLUS_3",
        "current_gw": 1,
        "total_budget": 1000,
        "max_players_per_team": 3,
        "projection_source": "internal"
    })
    assert res.status_code == 200
    job_id = res.json()["job_id"]

    final_result = None
    for _ in range(15):
        time.sleep(0.5)
        st_res = client.get(f"/api/v1/optimize/status/{job_id}")
        assert st_res.status_code == 200
        st_data = st_res.json()
        if st_data["status"] == "COMPLETED":
            res_res = client.get(f"/api/v1/optimize/result/{job_id}")
            assert res_res.status_code == 200
            final_result = res_res.json()["result"]
            break

    assert final_result is not None
    assert len(final_result["starting_11"]) == 11
    assert len(final_result["bench"]) == 4
    assert final_result["current_gw_starting_xi_xp"] > 35.0
    assert final_result["captain"] is not None
    assert final_result["vice_captain"] is not None

def test_all_three_modes_produce_valid_results(client):
    """Verify Next GW, Medium Term, and Long Term modes produce valid horizon results."""
    modes = ["CURRENT_GW_ONLY", "CURRENT_GW_PLUS_3", "LONG_TERM"]
    for mode in modes:
        res = client.post("/api/v1/optimize/job", json={
            "mode": mode,
            "current_gw": 1,
            "total_budget": 1000,
            "max_players_per_team": 3,
            "projection_source": "internal"
        })
        assert res.status_code == 200
        job_id = res.json()["job_id"]

        for _ in range(15):
            time.sleep(0.5)
            st_res = client.get(f"/api/v1/optimize/status/{job_id}")
            if st_res.json()["status"] == "COMPLETED":
                r_res = client.get(f"/api/v1/optimize/result/{job_id}")
                r_data = r_res.json()["result"]
                assert len(r_data["starting_11"]) == 11
                assert r_data["optimization_mode"] == mode
                break

def test_index_html_has_redesigned_broadcast_components(client):
    """Verify frontend HTML contains Dark Stadium Broadcast visual components."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "FPL AI" in html
    assert "2026/27 DECISION ENGINE" in html
    assert "hero-scoreboard" in html
    assert "mode-select" in html
    assert "pitch-container" in html
    assert "diagnostics-panel-title" in html
    assert "my-team-bank" in html
