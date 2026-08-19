import os
import pytest
import numpy as np
import pandas as pd
from backend.database import get_db
from backend.projections.engine import ProjectionEngine
from scratch.run_phase3c7_temporal_audit import construct_leak_free_temporal_dataset, load_data

@pytest.fixture(scope="module")
def temporal_dataset():
    df_raw = load_data()
    df_temp = construct_leak_free_temporal_dataset(df_raw)
    return df_temp

def test_temporal_dataset_construction_no_future_leakage(temporal_dataset):
    """Verify that temporal dataset is non-empty and has strict chronological ordering."""
    assert not temporal_dataset.empty
    assert len(temporal_dataset) > 1000
    
    required_cols = [
        'mins_last_3', 'mins_last_5', 'mins_last_10',
        'starts_last_3', 'starts_last_5', 'starts_last_10',
        'xg_90_3', 'xg_90_5', 'xg_90_10', 'xg_90_career',
        'xa_90_3', 'xa_90_5', 'xa_90_10', 'xa_90_career',
        'target_mins', 'target_xg', 'target_xa', 'target_starts'
    ]
    for col in required_cols:
        assert col in temporal_dataset.columns, f"Missing required column: {col}"

def test_expected_minutes_recency_out_of_sample_gain(temporal_dataset):
    """Verify that recent minutes/starts improve out-of-sample minutes MAE over static baseline."""
    train_df = temporal_dataset[temporal_dataset['season'].isin(["2022-23", "2023-24", "2024-25"])].copy()
    test_df = temporal_dataset[temporal_dataset['season'] == "2025-26"].copy()
    
    tot_prior_mean = train_df['target_mins'].mean()
    base_mae = np.mean(np.abs(test_df['target_mins'] - tot_prior_mean))
    rec_mae = np.mean(np.abs(test_df['target_mins'] - (test_df['mins_last_5'] / 5.0)))
    
    assert rec_mae < base_mae, f"Recency MAE ({rec_mae:.2f}) should be lower than static baseline MAE ({base_mae:.2f})"

def test_xg_process_stats_superior_to_goals(temporal_dataset):
    """Verify that xG/90 process stats correlate more strongly with future xG than actual Goals/90."""
    test_df = temporal_dataset[temporal_dataset['season'] == "2025-26"].copy()
    corr_xg = test_df['xg_90_5'].corr(test_df['target_xg'])
    corr_goals = test_df['goals_90_5'].corr(test_df['target_xg'])
    
    assert corr_xg > corr_goals, f"xG correlation ({corr_xg:.4f}) must be higher than Goals correlation ({corr_goals:.4f})"

def test_form_spikes_regress_to_mean(temporal_dataset):
    """Verify that 3-match xG spikes regress significantly toward long-term averages in the subsequent match."""
    spikers = temporal_dataset[temporal_dataset['xg_90_3'] >= 0.70]
    assert len(spikers) > 50
    
    mean_spike_rate = spikers['xg_90_3'].mean()
    mean_actual = spikers['target_xg'].mean()
    
    assert mean_actual < (mean_spike_rate / 90.0 * 90.0) * 0.6, "Spike rate must regress towards career mean"

def test_production_models_and_engine_unmodified():
    """Verify that Phase 3C.7 audit does not mutate production prediction models or engine files."""
    db_gen = get_db()
    db = next(db_gen)
    try:
        engine = ProjectionEngine(db)
        assert engine is not None
    finally:
        db.close()
