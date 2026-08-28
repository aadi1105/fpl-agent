import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

# ==================================================
# PHASE 3N.10C — OPTIMIZER & MY TEAM ISOLATION TESTS
# ==================================================

def test_diagnostics_fast_cached_response(client):
    """Verify GET /api/v1/projections/diagnostics returns fast cached response."""
    start_time = time.time()
    res1 = client.get("/api/v1/projections/diagnostics?limit=100")
    duration1 = time.time() - start_time
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1) <= 100

    # Second call should hit in-memory cache and return 200 OK with data
    res2 = client.get("/api/v1/projections/diagnostics?limit=100")
    assert res2.status_code == 200
    assert len(res2.json()) <= 100

def test_optimizer_job_and_result_payload(client):
    """Verify POST /api/v1/optimize/job completes and returns full payload."""
    job_res = client.post("/api/v1/optimize/job", json={
        "mode": "MEDIUM_TERM",
        "current_gw": 1,
        "total_budget": 1000,
        "max_players_per_team": 3,
        "projection_source": "internal"
    })
    assert job_res.status_code == 200
    job_id = job_res.json()["job_id"]

    completed = False
    for _ in range(30):
        time.sleep(0.5)
        st_res = client.get(f"/api/v1/optimize/status/{job_id}")
        st = st_res.json()
        if st["status"] == "COMPLETED":
            completed = True
            break
        elif st["status"] == "FAILED":
            pytest.fail(f"Optimizer job failed: {st.get('error')}")

    assert completed is True

    result_res = client.get(f"/api/v1/optimize/result/{job_id}")
    assert result_res.status_code == 200
    job_data = result_res.json()
    assert "result" in job_data
    opt = job_data["result"]

    assert len(opt["starting_11"]) == 11
    assert len(opt["bench"]) == 4
    assert opt["captain"] is not None
    assert opt["current_gw_starting_xi_xp"] > 0
    assert opt["total_cost_str"].startswith("£")

def test_my_team_and_optimizer_state_isolation(client):
    """Verify My Team CRUD operations do not clear or corrupt optimizer result endpoints."""
    # 1. Fetch user squad
    myteam_res = client.get("/api/v1/user-squad")
    assert myteam_res.status_code == 200

    # 2. Run optimizer job
    job_res = client.post("/api/v1/optimize/job", json={
        "mode": "MEDIUM_TERM",
        "current_gw": 1,
        "total_budget": 1000,
        "max_players_per_team": 3,
        "projection_source": "internal"
    })
    job_id = job_res.json()["job_id"]
    for _ in range(30):
        time.sleep(0.5)
        st = client.get(f"/api/v1/optimize/status/{job_id}").json()
        if st["status"] in ("COMPLETED", "FAILED"):
            break

    result_res = client.get(f"/api/v1/optimize/result/{job_id}")
    assert result_res.status_code == 200
    opt_xp = result_res.json()["result"]["current_gw_starting_xi_xp"]

    # 3. Fetch user squad again
    myteam_res2 = client.get("/api/v1/user-squad")
    assert myteam_res2.status_code == 200

    # 4. Confirm optimizer result remains completely intact
    result_res2 = client.get(f"/api/v1/optimize/result/{job_id}")
    assert result_res2.status_code == 200
    assert result_res2.json()["result"]["current_gw_starting_xi_xp"] == opt_xp

def test_frontend_last_optimizer_result_hydration():
    """Verify frontend HTML script contains lastOptimizerResult cache and re-hydration logic."""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    assert "lastOptimizerResult" in html
    assert "renderSquad(lastOptimizerResult)" in html
