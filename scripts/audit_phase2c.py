import os
import pickle
import json
import pandas as pd
import numpy as np
from backend.ml.minutes_model import FEATURE_COLS, DATA_PATH, MODEL_DIR

def run_phase2c_audit():
    print("=== PHASE 2C: ML MINUTES MODEL AUDIT & CALIBRATION ANALYSIS ===")
    
    # Load dataset & split test set
    df = pd.read_csv(DATA_PATH)
    df['home_away_is_home'] = (df['home_away'] == 'H').astype(int)
    df['pos_DEF'] = (df['position'] == 'DEF').astype(int)
    df['pos_MID'] = (df['position'] == 'MID').astype(int)
    df['pos_FWD'] = (df['position'] == 'FWD').astype(int)

    test_df = df[df['split'] == 'test'].reset_index(drop=True)
    X_test = test_df[FEATURE_COLS]

    # Load artifacts
    with open(os.path.join(MODEL_DIR, "minutes_start_v1.pkl"), "rb") as f:
        m_start = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "minutes_regression_v1.pkl"), "rb") as f:
        m_mins = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "minutes_60plus_v1.pkl"), "rb") as f:
        m_60 = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "minutes_zero_v1.pkl"), "rb") as f:
        m_0 = pickle.load(f)

    # 1. Calibration Bucket Analysis for P(start)
    prob_start = m_start.predict_proba(X_test)[:, 1]
    y_start = test_df['target_started'].values
    
    print("\n--- 1. P(start) Calibration Bucket Analysis (2025/26 Test Set) ---")
    print(f"{'Probability Range':<20} | {'Count':<8} | {'Avg Predicted P':<16} | {'Actual Start Rate':<18} | {'Abs Error':<10}")
    print("-" * 80)
    bins = np.linspace(0.0, 1.0, 11)
    for i in range(10):
        low, high = bins[i], bins[i+1]
        mask = (prob_start >= low) & (prob_start < high) if i < 9 else (prob_start >= low) & (prob_start <= high)
        cnt = np.sum(mask)
        if cnt > 0:
            avg_pred = np.mean(prob_start[mask])
            actual_rate = np.mean(y_start[mask])
            err = abs(avg_pred - actual_rate)
            print(f"[{low:.1f} - {high:.1f}]           | {cnt:<8} | {avg_pred:<16.4f} | {actual_rate:<18.4f} | {err:<10.4f}")

    # 2. Sample Size Subgroup MAE Analysis
    pred_mins = np.clip(m_mins.predict(X_test), 0, 180)
    test_df['pred_mins'] = pred_mins
    test_df['abs_err'] = np.abs(test_df['target_minutes'] - test_df['pred_mins'])

    print("\n--- 2. Historical Minutes Sample-Size Subgroup Analysis ---")
    print(f"{'Sample-Size Bucket':<25} | {'Count':<8} | {'Baseline MAE':<15} | {'ML MAE':<10} | {'Improvement':<12}")
    print("-" * 80)
    test_df['base_mins'] = test_df['average_minutes_last_5']
    test_df['base_err'] = np.abs(test_df['target_minutes'] - test_df['base_mins'])

    buckets = [
        ("< 300 Mins", test_df['minutes_last_10'] < 300),
        ("300 - 600 Mins", (test_df['minutes_last_10'] >= 300) & (test_df['minutes_last_10'] < 600)),
        ("600 - 1000 Mins", (test_df['minutes_last_10'] >= 600) & (test_df['minutes_last_10'] < 1000)),
        ("> 1000 Mins", test_df['minutes_last_10'] >= 1000)
    ]
    for label, mask in buckets:
        cnt = np.sum(mask)
        if cnt > 0:
            b_mae = test_df[mask]['base_err'].mean()
            m_mae = test_df[mask]['abs_err'].mean()
            imp = b_mae - m_mae
            print(f"{label:<25} | {cnt:<8} | {b_mae:<15.2f} | {m_mae:<10.2f} | {imp:<+12.2f}")

    # 3. Top 5 Error Cases Audit
    print("\n--- 3. Error Analysis: Top 5 Large Test-Set Prediction Errors ---")
    top_errors = test_df.sort_values(by='abs_err', ascending=False).head(5)
    for idx, row in top_errors.iterrows():
        print(f"Player: {row['player_name']} ({row['team']}) | GW{row['gameweek']} vs {row['opponent']}")
        print(f"  Pre-Deadline Prior Stats: mins_last_1={row['minutes_last_1']}, avg_mins_last_5={row['average_minutes_last_5']:.1f}")
        print(f"  Predicted xMins={row['pred_mins']:.1f} vs Actual Target Mins={row['target_minutes']} (Error: {row['abs_err']:.1f} mins)")
        print()

if __name__ == "__main__":
    run_phase2c_audit()
