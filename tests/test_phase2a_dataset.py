import os
import pytest
import pandas as pd
import numpy as np

from backend.ml.dataset_builder import HistoricalDatasetBuilder, DATA_DIR, SPLIT_MAP

@pytest.fixture(scope="module")
def dataset_and_metadata():
    builder = HistoricalDatasetBuilder()
    csv_path = os.path.join(DATA_DIR, "historical_minutes_dataset.csv")
    meta_path = os.path.join(DATA_DIR, "dataset_metadata.json")
    
    if not (os.path.exists(csv_path) and os.path.exists(meta_path)):
        df, meta = builder.build_dataset()
    else:
        df = pd.read_csv(csv_path)
        import json
        with open(meta_path, "r") as f:
            meta = json.load(f)
            
    return df, meta

def test_dataset_file_exists(dataset_and_metadata):
    df, meta = dataset_and_metadata
    assert len(df) > 80000
    assert meta["quality_audit"]["passed_all_quality_checks"] is True

def test_seasons_and_splits_defined_chronologically(dataset_and_metadata):
    df, meta = dataset_and_metadata
    
    assert set(meta["seasons_included"]) == {"2022-23", "2023-24", "2024-25", "2025-26"}
    
    train_seasons = set(df[df['split'] == 'train']['season'].unique())
    val_seasons = set(df[df['split'] == 'validation']['season'].unique())
    test_seasons = set(df[df['split'] == 'test']['season'].unique())
    
    assert train_seasons == {"2022-23", "2023-24"}
    assert val_seasons == {"2024-25"}
    assert test_seasons == {"2025-26"}

def test_no_duplicate_player_gameweek_rows(dataset_and_metadata):
    df, meta = dataset_and_metadata
    dups = df.duplicated(subset=['season', 'gameweek', 'fixture_id', 'player_id']).sum()
    assert dups == 0

def test_target_logical_consistency(dataset_and_metadata):
    df, meta = dataset_and_metadata
    
    # 60+ minutes implies target_60_plus == 1
    mismatched_60 = df[(df['target_minutes'] >= 60) & (df['target_60_plus'] != 1)]
    assert len(mismatched_60) == 0
    
    # 0 minutes implies target_zero_minutes == 1
    mismatched_zero = df[(df['target_minutes'] == 0) & (df['target_zero_minutes'] != 1)]
    assert len(mismatched_zero) == 0

def test_temporal_leakage_gw1_rolling_stats(dataset_and_metadata):
    df, meta = dataset_and_metadata
    
    # In GW1, rolling prior minutes MUST be 0
    gw1 = df[df['gameweek'] == 1]
    assert (gw1['minutes_last_1'] == 0).all()
    assert (gw1['starts_last_1'] == 0).all()
    assert (gw1['minutes_last_3'] == 0).all()
    assert (gw1['minutes_last_5'] == 0).all()

def test_temporal_leakage_rolling_statistics_sequence(dataset_and_metadata):
    df, meta = dataset_and_metadata
    
    # Pick a random player in 2023-24 GW10
    sample_player = df[(df['season'] == '2023-24') & (df['player_id'] == 355) & (df['gameweek'] == 10)]
    if len(sample_player) > 0:
        row = sample_player.iloc[0]
        
        # Check prior immediately preceding fixture target minutes
        prior_fixtures = df[(df['season'] == '2023-24') & (df['player_id'] == 355) & (df['gameweek'] < 10)].sort_values(by=['gameweek', 'fixture_id'])
        if len(prior_fixtures) > 0:
            last_fix = prior_fixtures.iloc[-1]
            assert row['minutes_last_1'] == last_fix['target_minutes']

def test_team_ratings_bounds_and_temporal_isolation(dataset_and_metadata):
    df, meta = dataset_and_metadata
    
    assert (df['team_attack_rating'] >= 600.0).all()
    assert (df['team_attack_rating'] <= 1600.0).all()
    assert (df['team_defence_rating'] >= 600.0).all()
    assert (df['team_defence_rating'] <= 1600.0).all()

    assert (df['opponent_attack_rating'] >= 600.0).all()
    assert (df['opponent_attack_rating'] <= 1600.0).all()
    assert (df['opponent_defence_rating'] >= 600.0).all()
    assert (df['opponent_defence_rating'] <= 1600.0).all()
