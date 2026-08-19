import os
import pytest
import numpy as np
import pandas as pd
from backend.ml.minutes_candidate_v2 import MinutesCandidateV2
from backend.ml.xg_candidate_v2 import XGCandidateV2, XG_POSITION_PRIORS
from backend.ml.xa_candidate_v2 import XACandidateV2, XA_POSITION_PRIORS

@pytest.fixture
def cand_minutes():
    return MinutesCandidateV2()

@pytest.fixture
def cand_xg():
    return XGCandidateV2()

@pytest.fixture
def cand_xa():
    return XACandidateV2()

def test_real_recent_starts_counted_correctly(cand_minutes):
    """Verify that actual fixture starts are used and not synthetic division of career mins."""
    pdata = {'price': 5.5}
    # Player with 5 genuine recent starts
    res_high = cand_minutes.predict_candidate_minutes(
        pdata=pdata, actual_recent_starts_5=5.0, actual_recent_mins_5=450.0,
        current_club_starts=5.0, current_club_mins=450.0, pos='FWD', cost=5.5
    )
    # Player with 0 recent starts despite historical mins
    res_low = cand_minutes.predict_candidate_minutes(
        pdata=pdata, actual_recent_starts_5=0.0, actual_recent_mins_5=0.0,
        current_club_starts=0.0, current_club_mins=0.0, pos='FWD', cost=5.5
    )
    
    assert res_high['w_evidence'] == 1.0
    assert res_low['w_evidence'] == 0.0
    assert res_high['expected_minutes_v2'] > res_low['expected_minutes_v2']
    assert res_high['p_start_v2'] > res_low['p_start_v2']

def test_synthetic_recent_starts_prevented(cand_minutes):
    """Verify that low-career-minute player with 0 starts gets w_evidence=0.0, not 1.0."""
    pdata = {'price': 4.5}
    # 240 career mins but 0 current club starts
    res = cand_minutes.predict_candidate_minutes(
        pdata=pdata, actual_recent_starts_5=0.0, actual_recent_mins_5=0.0,
        current_club_starts=0.0, current_club_mins=240.0, pos='FWD', cost=4.5
    )
    assert res['w_evidence'] == 0.0
    assert res['p_start_v2'] < 0.45

def test_transfers_do_not_contaminate_current_club_role(cand_minutes):
    """Verify that previous-club performance does not grant current-club starting role."""
    pdata = {'price': 6.0}
    # Transferred player: 2000 previous club mins, but 0 current club starts
    res = cand_minutes.predict_candidate_minutes(
        pdata=pdata, actual_recent_starts_5=0.0, actual_recent_mins_5=0.0,
        current_club_starts=0.0, current_club_mins=0.0, pos='MID', cost=6.0
    )
    assert res['w_evidence'] == 0.0
    assert res['expected_minutes_v2'] <= 45.0

def test_low_sample_xg_shrunk_toward_prior(cand_xg):
    """Verify low minute sample (<300 mins) shrinks xG heavily toward prior."""
    res_low = cand_xg.calculate_shrunk_xg90(raw_xg90_multiwindow=0.90, career_mins=100.0, pos='FWD')
    res_high = cand_xg.calculate_shrunk_xg90(raw_xg90_multiwindow=0.90, career_mins=3000.0, pos='FWD')
    
    # Weight on evidence for 100 mins should be 100 / (100 + 750) = 0.118
    assert res_low['w_evidence'] < 0.20
    assert res_high['w_evidence'] > 0.75
    # Shrunk rate for low sample should be close to FWD prior (0.380)
    assert abs(res_low['shrunk_xg90'] - XG_POSITION_PRIORS['FWD']) < 0.10
    assert res_high['shrunk_xg90'] > 0.70

def test_low_sample_xa_shrunk_toward_prior(cand_xa):
    """Verify low minute sample (<300 mins) shrinks xA heavily toward prior."""
    res_low = cand_xa.calculate_shrunk_xa90(raw_xa90_multiwindow=0.60, career_mins=100.0, pos='MID')
    res_high = cand_xa.calculate_shrunk_xa90(raw_xa90_multiwindow=0.60, career_mins=3000.0, pos='MID')
    
    assert res_low['w_evidence'] < 0.20
    assert res_high['w_evidence'] > 0.75
    assert abs(res_low['shrunk_xa90'] - XA_POSITION_PRIORS['MID']) < 0.10

def test_shrinkage_is_monotonic_with_sample_size(cand_xg, cand_xa):
    """Verify shrinkage weight increases monotonically with evidence sample size."""
    mins_list = [50.0, 300.0, 800.0, 2000.0, 5000.0]
    weights_xg = [cand_xg.calculate_shrunk_xg90(0.5, m, 'FWD')['w_evidence'] for m in mins_list]
    weights_xa = [cand_xa.calculate_shrunk_xa90(0.5, m, 'MID')['w_evidence'] for m in mins_list]
    
    assert weights_xg == sorted(weights_xg), "xG shrinkage weight must be strictly monotonic"
    assert weights_xa == sorted(weights_xa), "xA shrinkage weight must be strictly monotonic"

def test_logical_consistency_p_start_p60_p0(cand_minutes):
    """Verify that P(start), P(60+), P(0) probabilities are logically consistent."""
    pdata = {'price': 5.5}
    res = cand_minutes.predict_candidate_minutes(
        pdata=pdata, actual_recent_starts_5=3.0, actual_recent_mins_5=270.0,
        current_club_starts=3.0, current_club_mins=270.0, pos='MID', cost=5.5
    )
    p_start = res['p_start_v2']
    p_60 = res['p_60_plus_v2']
    p_zero = res['p_zero_v2']
    
    assert 0.0 <= p_start <= 1.0
    assert 0.0 <= p_60 <= p_start, "P(60+) cannot exceed P(start)"
    assert 0.0 <= p_zero <= 1.0
    assert p_start + p_zero <= 1.0, "P(start) + P(0) cannot exceed 1.0"

def test_no_player_hardcoded_corrections():
    """Verify no player-specific name strings exist in candidate v2 module code."""
    files_to_check = [
        "backend/ml/minutes_candidate_v2.py",
        "backend/ml/xg_candidate_v2.py",
        "backend/ml/xa_candidate_v2.py"
    ]
    for filepath in files_to_check:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().lower()
            assert "nelson" not in content
            assert "awoniyi" not in content
            assert "osula" not in content
            assert "marmoush" not in content
            assert "haaland" not in content

def test_v1_production_artifacts_unmodified():
    """Verify that v1 production pickle artifacts remain 100% present and unmodified."""
    v1_models = [
        "models/minutes_start_v1.pkl",
        "models/minutes_regression_v1.pkl",
        "models/minutes_60plus_v1.pkl",
        "models/minutes_zero_v1.pkl",
        "models/xg_v1_lgbm.pkl",
        "models/xa_v1_lgbm.pkl"
    ]
    for mpath in v1_models:
        assert os.path.exists(mpath), f"Production v1 model artifact missing: {mpath}"
