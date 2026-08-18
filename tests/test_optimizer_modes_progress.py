import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.optimizer.progress_manager import progress_manager

client = TestClient(app)

def test_progress_manager_job_lifecycle():
    """Verify thread-safe job creation, status updates, completion and retrieval."""
    job_id = progress_manager.create_job("STRONG_XI_DUMP_BENCH")
    assert job_id is not None

    status = progress_manager.get_status(job_id)
    assert status['status'] == 'RUNNING'
    assert status['progress_percent'] == 10

    progress_manager.update_stage(job_id, 4, "Building MILP Constraints")
    status = progress_manager.get_status(job_id)
    assert status['stage_number'] == 5
    assert status['progress_percent'] == 50

    dummy_result = {"total_cost_str": "£100.0m", "weighted_horizon_xp": 77.5}
    progress_manager.complete_job(job_id, dummy_result)

    status = progress_manager.get_status(job_id)
    assert status['status'] == 'COMPLETED'
    assert status['progress_percent'] == 100

    result = progress_manager.get_result(job_id)
    assert result['result']['total_cost_str'] == "£100.0m"

def test_optimization_job_endpoints():
    """Verify API endpoints POST /api/v1/optimize/job and GET /api/v1/optimize/status/{job_id}."""
    payload = {
        "mode": "BALANCED_BENCH",
        "current_gw": 1,
        "total_budget": 1000,
        "max_players_per_team": 3,
        "projection_source": "internal"
    }

    res = client.post("/api/v1/optimize/job", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Check status endpoint
    status_res = client.get(f"/api/v1/optimize/status/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["job_id"] == job_id
    assert status_data["mode"] == "BALANCED_BENCH"

def test_mode_comparison_endpoint():
    """Verify POST /api/v1/optimize/compare_modes returns 4 distinct mode results."""
    payload = {
        "mode": "CURRENT_GW_PLUS_3",
        "current_gw": 1,
        "total_budget": 1000,
        "max_players_per_team": 3,
        "projection_source": "internal"
    }

    res = client.post("/api/v1/optimize/compare_modes", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["modes_compared"] == 4
    assert len(data["comparison"]) == 4

    modes_seen = [c["mode"] for c in data["comparison"]]
    assert "CURRENT_GW_PLUS_3" in modes_seen
    assert "STRONG_XI_DUMP_BENCH" in modes_seen
    assert "BALANCED_BENCH" in modes_seen
    assert "MAXIMUM_SQUAD" in modes_seen

def test_positional_percentiles_in_diagnostics():
    """Verify position-relative percentiles are calculated in projection diagnostics."""
    res = client.get("/api/v1/projections/diagnostics?target_gw=1&limit=20")
    assert res.status_code == 200
    diag = res.json()

    assert len(diag) > 0
    first_p = diag[0]
    assert "pos_price_percentile" in first_p
    assert "pos_xp_percentile" in first_p
    assert "pos_value_percentile" in first_p
    assert 0.0 <= first_p["pos_price_percentile"] <= 100.0
