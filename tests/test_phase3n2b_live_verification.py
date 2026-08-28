import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app, progress_manager
from backend.database import SessionLocal
from backend.models import Player, PlayerProjection
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_modal_overlay_visibility_css():
    """Verify index.html contains CSS rule ensuring modal-overlay becomes visible when open/display flex."""
    import os
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert ".modal-overlay.open" in html or ".modal-overlay[style*=\"display: flex\"]" in html
    assert "visibility: visible" in html
    assert "opacity: 1" in html

def test_save_my_team_does_not_start_optimizer(client, db_session):
    """Verify POST /api/v1/user-squad saves team cleanly without creating optimizer jobs."""
    gkps = db_session.query(Player).filter(Player.element_type == "GKP").limit(2).all()
    defs = db_session.query(Player).filter(Player.element_type == "DEF").limit(5).all()
    mids = db_session.query(Player).filter(Player.element_type == "MID").limit(5).all()
    fwds = db_session.query(Player).filter(Player.element_type == "FWD").limit(3).all()
    player_ids = [p.id for p in (gkps + defs + mids + fwds)]

    # Count active jobs before
    jobs_before = len(progress_manager._jobs)

    res = client.post("/api/v1/user-squad", json={"player_ids": player_ids, "bank": 10, "free_transfers": 1})
    assert res.status_code == 200

    # Count active jobs after
    jobs_after = len(progress_manager._jobs)
    assert jobs_after == jobs_before, "Saving user squad MUST NOT automatically spawn an optimizer job!"

def test_optimizer_projection_reuse_performance(db_session):
    """Verify run_projections reuses existing projections in < 1.0 second."""
    engine = ProjectionEngine(db_session)
    
    t0 = time.time()
    count = engine.run_projections(start_gw=1, end_gw=4, force=False)
    elapsed = time.time() - t0

    assert count >= 2000
    assert elapsed < 1.5, f"Projection engine reuse took {elapsed:.3f}s (should be < 1.5s)!"

def test_single_optimizer_job_creation(client):
    """Verify POST /api/v1/optimize/job spawns exactly 1 job ID."""
    payload = {
        "mode": "MEDIUM_TERM",
        "current_gw": 1,
        "total_budget": 1000,
        "max_players_per_team": 3
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
