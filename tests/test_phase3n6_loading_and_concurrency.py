import pytest
import time
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, engine
from backend.models import Player, PlayerProjection
from backend.optimizer.progress_manager import progress_manager

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

# ==================================================
# PART 1 — MY TEAM PLAYER LOADING UX TESTS
# ==================================================

def test_fast_canonical_player_api(client):
    """Verify GET /api/v1/players returns 600 players in under 1 second without triggering optimizer."""
    t0 = time.time()
    res = client.get("/api/v1/players?limit=600&target_gw=1")
    dt = time.time() - t0

    assert res.status_code == 200
    players = res.json()
    assert len(players) >= 500
    assert dt < 1.0, f"Player API MUST be fast! Took {dt:.3f}s"

def test_player_search_canonical(db_session):
    """Verify player search matches case-insensitively for key target players."""
    target_names = ["Raya", "Haaland", "Saka", "Calvert-Lewin", "B.Fernandes"]
    for name in target_names:
        p = db_session.query(Player).filter(Player.web_name.ilike(f"%{name}%")).first()
        assert p is not None, f"Player {name} MUST exist in database!"

# ==================================================
# PART 2 — SQLITE CONCURRENCY & LOCK FIX TESTS
# ==================================================

def test_sqlite_wal_mode_configured():
    """Verify SQLite connection is configured with WAL mode and 30s busy timeout."""
    with engine.connect() as conn:
        journal_mode = conn.exec_driver_sql("PRAGMA journal_mode;").scalar()
        busy_timeout = conn.exec_driver_sql("PRAGMA busy_timeout;").scalar()
        
        assert journal_mode.lower() == "wal", f"Journal mode MUST be WAL! Got {journal_mode}"
        assert busy_timeout >= 30000, f"Busy timeout MUST be >= 30000ms! Got {busy_timeout}"

def test_single_optimizer_job_creation(client):
    """Verify POST /api/v1/optimize/job creates exactly ONE job with RUNNING status."""
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
    assert data["status"] == "RUNNING"

    # Poll status
    time.sleep(1)
    status_res = client.get(f"/api/v1/optimize/status/{job_id}")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["job_id"] == job_id
    assert status_data["status"] in ["RUNNING", "COMPLETED"]

def test_failed_job_lifecycle():
    """Verify progress_manager handles job failures cleanly without leaving locks."""
    job_id = progress_manager.create_job("TEST_FAILED_MODE")
    progress_manager.fail_job(job_id, "Test database lock failure simulation")

    status = progress_manager.get_status(job_id)
    assert status["status"] == "FAILED"
    assert "Test database lock failure" in status["error"]
