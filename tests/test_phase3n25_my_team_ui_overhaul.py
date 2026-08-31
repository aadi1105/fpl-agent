import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

# ==================================================
# PHASE 3N.25 — MY TEAM COMMAND CENTER UI OVERHAUL TESTS
# ==================================================

def test_my_team_tab_contains_integrated_control_strip(client):
    """Verify My Team tab contains the compact team-control-strip and required management controls."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert 'id="tab-my-team"' in html
    assert 'class="team-control-strip"' in html
    assert 'id="my-team-header-stats"' in html
    assert 'id="my-team-count-stat"' in html
    assert 'id="my-team-bank-stat"' in html
    assert 'id="my-team-ft-stat"' in html
    assert 'id="edit-my-team-btn"' in html
    assert 'id="compare-my-team-btn"' in html
    assert 'id="my-team-gw-select"' in html

def test_my_team_tab_contains_broadcast_scoreboard_strip(client):
    """Verify My Team tab contains the broadcast-scoreboard-strip overlay and hero score elements."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert 'id="gw-scoreboard-card"' in html
    assert 'class="broadcast-scoreboard-strip"' in html
    assert 'id="scoreboard-title"' in html
    assert 'id="scoreboard-score"' in html
    assert 'id="scoreboard-score-unit"' in html
    assert 'id="scoreboard-captain-bonus"' in html
    assert 'id="scoreboard-bench"' in html
    assert 'id="scoreboard-transfers"' in html
    assert 'id="scoreboard-overall"' in html
    assert 'id="scoreboard-chip"' in html
    assert 'id="scoreboard-live-indicator"' in html

def test_pitch_and_substitutes_strip_structure(client):
    """Verify pitch centerpiece and attached substitutes bench technical strip are present."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert 'id="my-team-formation"' in html
    assert 'id="my-team-gkp"' in html
    assert 'id="my-team-def"' in html
    assert 'id="my-team-mid"' in html
    assert 'id="my-team-fwd"' in html
    assert 'id="my-team-bench"' in html

def test_financial_state_and_transfer_intelligence_hub(client):
    """Verify right-column technical and tactical hub elements are present."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert 'id="my-team-bank"' in html
    assert 'id="my-team-fts"' in html
    assert 'id="my-team-starting-xp"' in html
    assert 'id="comp-transfers-table-container"' in html

def test_season_chips_grid_and_season_history_log(client):
    """Verify Season Chips grid and Season Gameweek Log summary & table are present."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert 'id="chips-status-grid"' in html
    assert 'id="hist-sum-total"' in html
    assert 'id="hist-sum-avg"' in html
    assert 'id="hist-sum-best"' in html
    assert 'id="hist-sum-worst"' in html
    assert 'id="hist-sum-rank"' in html
    assert 'id="hist-sum-xfers"' in html
    assert 'id="season-history-tbody"' in html
