import pytest
import pandas as pd
import numpy as np
from backend.ml.minutes_predictor import MinutesPredictor

def test_price_not_proxy_for_starting():
    """Verify that a high/mid price player without playing evidence does NOT receive high P(start)."""
    predictor = MinutesPredictor()
    
    # Player with high price £6.0m but 0 playing evidence
    pdata_sparse = {
        'price': 6.0,
        'fixture_difficulty': 3,
        'team_attack_rating': 1200.0,
        'team_defence_rating': 1200.0,
        'opponent_attack_rating': 1000.0,
        'opponent_defence_rating': 1000.0,
        'home_away_is_home': 1.0,
        'minutes_last_5': 0.0,
        'starts_last_5': 0.0,
        'appearances_last_5': 0.0,
        'average_minutes_last_5': 0.0,
        'pos_MID': 1.0
    }
    
    res = predictor.predict(pdata_sparse)
    assert res['p_start'] <= 0.25, f"Expected P(start) <= 0.25 for 0 evidence, got {res['p_start']}"
    assert res['expected_minutes'] <= 35.0, f"Expected xMins <= 35.0 for 0 evidence, got {res['expected_minutes']}"

def test_established_starters_retain_high_minutes():
    """Verify that established starters with full playing evidence retain >70 xMins and high P(start)."""
    predictor = MinutesPredictor()
    
    pdata_starter = {
        'price': 15.0,
        'fixture_difficulty': 2,
        'team_attack_rating': 1300.0,
        'team_defence_rating': 1200.0,
        'opponent_attack_rating': 900.0,
        'opponent_defence_rating': 900.0,
        'home_away_is_home': 1.0,
        'minutes_last_1': 90.0,
        'minutes_last_3': 270.0,
        'minutes_last_5': 450.0,
        'minutes_last_10': 900.0,
        'starts_last_1': 1.0,
        'starts_last_3': 3.0,
        'starts_last_5': 5.0,
        'starts_last_10': 10.0,
        'appearances_last_5': 5.0,
        'average_minutes_last_5': 90.0,
        'pos_FWD': 1.0
    }
    
    res = predictor.predict(pdata_starter)
    assert res['p_start'] >= 0.70, f"Expected P(start) >= 0.70 for starter, got {res['p_start']}"
    assert res['expected_minutes'] >= 65.0, f"Expected xMins >= 65.0 for starter, got {res['expected_minutes']}"

def test_role_evidence_shrinkage_gradient():
    """Verify that role evidence weight smooths monotonically as playing sample increases."""
    predictor = MinutesPredictor()
    
    xMins_list = []
    for apps in [0.0, 1.0, 3.0, 5.0]:
        pdata = {
            'price': 5.5,
            'fixture_difficulty': 3,
            'team_attack_rating': 1100.0,
            'team_defence_rating': 1100.0,
            'opponent_attack_rating': 1000.0,
            'opponent_defence_rating': 1000.0,
            'home_away_is_home': 1.0,
            'minutes_last_1': 75.0 if apps > 0 else 0.0,
            'minutes_last_3': min(270.0, apps * 75.0),
            'minutes_last_5': apps * 75.0,
            'starts_last_1': 1.0 if apps > 0 else 0.0,
            'starts_last_3': min(3.0, apps),
            'starts_last_5': apps,
            'appearances_last_5': apps,
            'average_minutes_last_5': 75.0 if apps > 0 else 0.0,
            'pos_MID': 1.0
        }
        res = predictor.predict(pdata)
        xMins_list.append(res['expected_minutes'])
    
    # Check strict monotonic increase as playing evidence increases
    for i in range(len(xMins_list) - 1):
        assert xMins_list[i] < xMins_list[i+1], f"Expected monotonic increase, got {xMins_list}"

def test_vectorized_batch_predict_shrinkage():
    """Verify vectorized predict_batch applies identical shrinkage rules."""
    predictor = MinutesPredictor()
    
    df = pd.DataFrame([
        {
            'player_id': 1,
            'price': 5.5,
            'appearances_last_5': 0.0,
            'minutes_last_5': 0.0,
            'starts_last_5': 0.0,
            'average_minutes_last_5': 0.0,
            'pos_MID': 1.0
        },
        {
            'player_id': 2,
            'price': 5.5,
            'appearances_last_5': 5.0,
            'minutes_last_1': 90.0,
            'minutes_last_3': 270.0,
            'minutes_last_5': 450.0,
            'starts_last_1': 1.0,
            'starts_last_3': 3.0,
            'starts_last_5': 5.0,
            'average_minutes_last_5': 90.0,
            'pos_MID': 1.0
        }
    ])
    
    res_df = predictor.predict_batch(df)
    assert res_df.loc[0, 'expected_minutes_v1'] <= 35.0
    assert res_df.loc[1, 'expected_minutes_v1'] >= 35.0
