import os
import sys
import json
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, brier_score_loss

np.random.seed(42)

RAW_FILES = {
    "2022-23": "data/raw/merged_gw_2022-23.csv",
    "2023-24": "data/raw/merged_gw_2023-24.csv",
    "2024-25": "data/raw/merged_gw_2024-25.csv",
    "2025-26": "data/raw/merged_gw_2025-26.csv"
}

def load_data():
    all_dfs = []
    for s_name, path in RAW_FILES.items():
        if os.path.exists(path):
            df_season = pd.read_csv(path)
            df_season['season'] = s_name
            all_dfs.append(df_season)
    df_raw = pd.concat(all_dfs, ignore_index=True)
    
    if 'GW' in df_raw.columns:
        df_raw['gameweek'] = df_raw['GW']
    if 'element' in df_raw.columns:
        df_raw['player_id'] = df_raw['element']
    if 'name' in df_raw.columns:
        df_raw['player_name'] = df_raw['name']
    
    for col in ['minutes', 'starts', 'goals_scored', 'assists', 'expected_goals', 'expected_assists', 'threat', 'creativity']:
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0.0)
            
    season_order = {"2022-23": 1, "2023-24": 2, "2024-25": 3, "2025-26": 4}
    df_raw['season_idx'] = df_raw['season'].map(season_order)
    df_raw = df_raw.sort_values(by=['season_idx', 'gameweek', 'player_id']).reset_index(drop=True)
    return df_raw

def construct_leak_free_temporal_dataset(df_raw):
    records = []
    grouped = df_raw.groupby('player_id')
    
    for player_id, p_df in grouped:
        p_df = p_df.sort_values(by=['season_idx', 'gameweek']).reset_index(drop=True)
        
        n_rows = len(p_df)
        mins_arr = p_df['minutes'].values
        starts_arr = p_df['starts'].values
        xg_arr = p_df['expected_goals'].values
        xa_arr = p_df['expected_assists'].values
        goals_arr = p_df['goals_scored'].values
        assists_arr = p_df['assists'].values
        threat_arr = p_df['threat'].values
        team_arr = p_df['team'].values
        season_arr = p_df['season'].values
        gw_arr = p_df['gameweek'].values
        pos_arr = p_df['position'].values if 'position' in p_df.columns else ['MID']*n_rows
        name_arr = p_df['player_name'].values
        
        for i in range(n_rows):
            target_mins = mins_arr[i]
            target_xg = xg_arr[i]
            target_xa = xa_arr[i]
            target_starts = starts_arr[i]
            
            if i == 0:
                mins_3 = mins_5 = mins_10 = 0.0
                starts_3 = starts_5 = starts_10 = 0.0
                xg_3 = xg_5 = xg_10 = 0.0
                xa_3 = xa_5 = xa_10 = 0.0
                goals_3 = goals_5 = goals_10 = 0.0
                assists_3 = assists_5 = assists_10 = 0.0
                threat_5 = 0.0
                tot_mins_prior = 0.0
                tot_xg_prior = 0.0
                tot_xa_prior = 0.0
                tot_goals_prior = 0.0
                curr_club_mins = 0.0
                curr_club_xg = 0.0
            else:
                p_mins = mins_arr[:i]
                p_starts = starts_arr[:i]
                p_xg = xg_arr[:i]
                p_xa = xa_arr[:i]
                p_goals = goals_arr[:i]
                p_assists = assists_arr[:i]
                p_threat = threat_arr[:i]
                p_teams = team_arr[:i]
                
                mins_3 = float(np.sum(p_mins[-3:]))
                mins_5 = float(np.sum(p_mins[-5:]))
                mins_10 = float(np.sum(p_mins[-10:]))
                
                starts_3 = float(np.sum(p_starts[-3:]))
                starts_5 = float(np.sum(p_starts[-5:]))
                starts_10 = float(np.sum(p_starts[-10:]))
                
                xg_3 = float(np.sum(p_xg[-3:]))
                xg_5 = float(np.sum(p_xg[-5:]))
                xg_10 = float(np.sum(p_xg[-10:]))
                
                xa_3 = float(np.sum(p_xa[-3:]))
                xa_5 = float(np.sum(p_xa[-5:]))
                xa_10 = float(np.sum(p_xa[-10:]))
                
                goals_3 = float(np.sum(p_goals[-3:]))
                goals_5 = float(np.sum(p_goals[-5:]))
                goals_10 = float(np.sum(p_goals[-10:]))
                
                assists_3 = float(np.sum(p_assists[-3:]))
                assists_5 = float(np.sum(p_assists[-5:]))
                assists_10 = float(np.sum(p_assists[-10:]))
                
                threat_5 = float(np.sum(p_threat[-5:]))
                
                tot_mins_prior = float(np.sum(p_mins))
                tot_xg_prior = float(np.sum(p_xg))
                tot_xa_prior = float(np.sum(p_xa))
                tot_goals_prior = float(np.sum(p_goals))
                
                curr_team = team_arr[i]
                curr_club_mask = (p_teams == curr_team)
                curr_club_mins = float(np.sum(p_mins[curr_club_mask]))
                curr_club_xg = float(np.sum(p_xg[curr_club_mask]))

            xg_90_3 = (xg_3 / (mins_3 / 90.0)) if mins_3 >= 45.0 else (tot_xg_prior / max(1.0, tot_mins_prior / 90.0))
            xg_90_5 = (xg_5 / (mins_5 / 90.0)) if mins_5 >= 45.0 else (tot_xg_prior / max(1.0, tot_mins_prior / 90.0))
            xg_90_10 = (xg_10 / (mins_10 / 90.0)) if mins_10 >= 45.0 else (tot_xg_prior / max(1.0, tot_mins_prior / 90.0))
            xg_90_career = (tot_xg_prior / (tot_mins_prior / 90.0)) if tot_mins_prior >= 90.0 else 0.35
            
            xa_90_3 = (xa_3 / (mins_3 / 90.0)) if mins_3 >= 45.0 else (tot_xa_prior / max(1.0, tot_mins_prior / 90.0))
            xa_90_5 = (xa_5 / (mins_5 / 90.0)) if mins_5 >= 45.0 else (tot_xa_prior / max(1.0, tot_mins_prior / 90.0))
            xa_90_10 = (xa_10 / (mins_10 / 90.0)) if mins_10 >= 45.0 else (tot_xa_prior / max(1.0, tot_mins_prior / 90.0))
            xa_90_career = (tot_xa_prior / (tot_mins_prior / 90.0)) if tot_mins_prior >= 90.0 else 0.15

            goals_90_5 = (goals_5 / (mins_5 / 90.0)) if mins_5 >= 45.0 else (tot_goals_prior / max(1.0, tot_mins_prior / 90.0))

            records.append({
                'season': season_arr[i],
                'gameweek': gw_arr[i],
                'player_id': player_id,
                'player_name': name_arr[i],
                'team': team_arr[i],
                'position': pos_arr[i],
                'mins_last_3': mins_3,
                'mins_last_5': mins_5,
                'mins_last_10': mins_10,
                'starts_last_3': starts_3,
                'starts_last_5': starts_5,
                'starts_last_10': starts_10,
                'xg_last_3': xg_3,
                'xg_last_5': xg_5,
                'xg_last_10': xg_10,
                'xa_last_3': xa_3,
                'xa_last_5': xa_5,
                'xa_last_10': xa_10,
                'goals_last_3': goals_3,
                'goals_last_5': goals_5,
                'goals_last_10': goals_10,
                'assists_last_3': assists_3,
                'assists_last_5': assists_5,
                'assists_last_10': assists_10,
                'threat_last_5': threat_5,
                'xg_90_3': xg_90_3,
                'xg_90_5': xg_90_5,
                'xg_90_10': xg_90_10,
                'xg_90_career': xg_90_career,
                'xa_90_3': xa_90_3,
                'xa_90_5': xa_90_5,
                'xa_90_10': xa_90_10,
                'xa_90_career': xa_90_career,
                'goals_90_5': goals_90_5,
                'tot_mins_prior': tot_mins_prior,
                'curr_club_mins': curr_club_mins,
                'target_mins': target_mins,
                'target_xg': target_xg,
                'target_xa': target_xa,
                'target_starts': target_starts
            })
            
    return pd.DataFrame(records)

def poisson_deviance(y_true, y_pred, eps=1e-9):
    y_pred = np.clip(y_pred, eps, None)
    y_true = np.clip(y_true, 0, None)
    dev = 2 * (y_true * np.log(np.maximum(eps, y_true) / y_pred) - (y_true - y_pred))
    return float(np.mean(dev))

print("Loading data and constructing dataset...")
df_temporal = construct_leak_free_temporal_dataset(load_data())

train_df = df_temporal[df_temporal['season'].isin(["2022-23", "2023-24", "2024-25"])].copy()
test_df = df_temporal[df_temporal['season'] == "2025-26"].copy()

# ==========================================
# 1. EXPECTED MINUTES AUDIT
# ==========================================
print("\n--- 1. EXPECTED MINUTES AUDIT ---")
mins_baseline_feats = ['tot_mins_prior', 'curr_club_mins']
mins_recency_feats = ['tot_mins_prior', 'curr_club_mins', 'mins_last_3', 'mins_last_5', 'mins_last_10', 'starts_last_3', 'starts_last_5', 'starts_last_10']

# Train baseline mins
m_mins_base = lgb.LGBMRegressor(n_estimators=100, random_state=42, verbose=-1)
m_mins_base.fit(train_df[mins_baseline_feats], train_df['target_mins'])
pred_mins_base = m_mins_base.predict(test_df[mins_baseline_feats])

# Train recency mins
m_mins_rec = lgb.LGBMRegressor(n_estimators=100, random_state=42, verbose=-1)
m_mins_rec.fit(train_df[mins_recency_feats], train_df['target_mins'])
pred_mins_rec = m_mins_rec.predict(test_df[mins_recency_feats])

mae_mins_base = mean_absolute_error(test_df['target_mins'], pred_mins_base)
rmse_mins_base = np.sqrt(mean_squared_error(test_df['target_mins'], pred_mins_base))
mae_mins_rec = mean_absolute_error(test_df['target_mins'], pred_mins_rec)
rmse_mins_rec = np.sqrt(mean_squared_error(test_df['target_mins'], pred_mins_rec))

print(f"Minutes Baseline MAE: {mae_mins_base:.2f} | RMSE: {rmse_mins_base:.2f}")
print(f"Minutes Recency  MAE: {mae_mins_rec:.2f} | RMSE: {rmse_mins_rec:.2f}")
print(f"Improvement: MAE {((mae_mins_base - mae_mins_rec)/mae_mins_base)*100:.2f}% | RMSE {((rmse_mins_base - rmse_mins_rec)/rmse_mins_base)*100:.2f}%")

# Train P(start) classification
m_start_base = lgb.LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
m_start_base.fit(train_df[mins_baseline_feats], train_df['target_starts'])
brier_start_base = brier_score_loss(test_df['target_starts'], m_start_base.predict_proba(test_df[mins_baseline_feats])[:, 1])

m_start_rec = lgb.LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
m_start_rec.fit(train_df[mins_recency_feats], train_df['target_starts'])
brier_start_rec = brier_score_loss(test_df['target_starts'], m_start_rec.predict_proba(test_df[mins_recency_feats])[:, 1])

print(f"P(start) Brier Score Baseline: {brier_start_base:.4f} | Recency: {brier_start_rec:.4f} (Improvement: {((brier_start_base - brier_start_rec)/brier_start_base)*100:.2f}%)")

# ==========================================
# 2. xG RECENCY AUDIT
# ==========================================
print("\n--- 2. xG RECENCY AUDIT ---")
xg_models = {
    "Model A (Baseline Career)": ['xg_90_career', 'tot_mins_prior'],
    "Model B (+ Last 10)": ['xg_90_career', 'tot_mins_prior', 'xg_90_10'],
    "Model C (+ Last 5)": ['xg_90_career', 'tot_mins_prior', 'xg_90_5'],
    "Model D (+ Last 3)": ['xg_90_career', 'tot_mins_prior', 'xg_90_3'],
    "Model E (Multi-window Recency)": ['xg_90_career', 'tot_mins_prior', 'xg_90_3', 'xg_90_5', 'xg_90_10', 'threat_last_5', 'goals_90_5']
}

xg_results = {}
for m_name, feats in xg_models.items():
    m = lgb.LGBMRegressor(objective='poisson', n_estimators=100, random_state=42, verbose=-1)
    m.fit(train_df[feats], train_df['target_xg'])
    preds = m.predict(test_df[feats])
    mae = mean_absolute_error(test_df['target_xg'], preds)
    rmse = np.sqrt(mean_squared_error(test_df['target_xg'], preds))
    dev = poisson_deviance(test_df['target_xg'].values, preds)
    xg_results[m_name] = {'mae': mae, 'rmse': rmse, 'deviance': dev}
    base_dev = xg_results["Model A (Baseline Career)"]['deviance']
    imp_dev = ((base_dev - dev) / base_dev) * 100
    print(f"{m_name:30s} | MAE: {mae:.4f} | RMSE: {rmse:.4f} | Deviance: {dev:.4f} (Imp: {imp_dev:+.2f}%)")

# ==========================================
# 3. xA RECENCY AUDIT
# ==========================================
print("\n--- 3. xA RECENCY AUDIT ---")
xa_models = {
    "Model A (Baseline Career)": ['xa_90_career', 'tot_mins_prior'],
    "Model B (+ Last 10)": ['xa_90_career', 'tot_mins_prior', 'xa_90_10'],
    "Model C (+ Last 5)": ['xa_90_career', 'tot_mins_prior', 'xa_90_5'],
    "Model D (+ Last 3)": ['xa_90_career', 'tot_mins_prior', 'xa_90_3'],
    "Model E (Multi-window Recency)": ['xa_90_career', 'tot_mins_prior', 'xa_90_3', 'xa_90_5', 'xa_90_10']
}

xa_results = {}
for m_name, feats in xa_models.items():
    m = lgb.LGBMRegressor(objective='poisson', n_estimators=100, random_state=42, verbose=-1)
    m.fit(train_df[feats], train_df['target_xa'])
    preds = m.predict(test_df[feats])
    mae = mean_absolute_error(test_df['target_xa'], preds)
    rmse = np.sqrt(mean_squared_error(test_df['target_xa'], preds))
    dev = poisson_deviance(test_df['target_xa'].values, preds)
    xa_results[m_name] = {'mae': mae, 'rmse': rmse, 'deviance': dev}
    base_dev = xa_results["Model A (Baseline Career)"]['deviance']
    imp_dev = ((base_dev - dev) / base_dev) * 100
    print(f"{m_name:30s} | MAE: {mae:.4f} | RMSE: {rmse:.4f} | Deviance: {dev:.4f} (Imp: {imp_dev:+.2f}%)")

# ==========================================
# 4. SAMPLE-SIZE INTERACTION
# ==========================================
print("\n--- 4. SAMPLE-SIZE INTERACTION ---")
sample_buckets = [
    ("<300 mins", 0, 300),
    ("300-600 mins", 300, 600),
    ("600-1000 mins", 600, 1000),
    ("1000-2000 mins", 1000, 2000),
    ("2000+ mins", 2000, 999999)
]

for b_name, b_min, b_max in sample_buckets:
    sub = test_df[(test_df['tot_mins_prior'] >= b_min) & (test_df['tot_mins_prior'] < b_max)]
    if len(sub) > 0:
        m_base = lgb.LGBMRegressor(objective='poisson', n_estimators=100, random_state=42, verbose=-1)
        m_base.fit(train_df[['xg_90_career', 'tot_mins_prior']], train_df['target_xg'])
        pred_base = m_base.predict(sub[['xg_90_career', 'tot_mins_prior']])
        
        m_rec = lgb.LGBMRegressor(objective='poisson', n_estimators=100, random_state=42, verbose=-1)
        m_rec.fit(train_df[['xg_90_career', 'tot_mins_prior', 'xg_90_5']], train_df['target_xg'])
        pred_rec = m_rec.predict(sub[['xg_90_career', 'tot_mins_prior', 'xg_90_5']])
        
        dev_b = poisson_deviance(sub['target_xg'].values, pred_base)
        dev_r = poisson_deviance(sub['target_xg'].values, pred_rec)
        print(f"Bucket {b_name:15s} (N={len(sub):4d}) | Baseline Dev: {dev_b:.4f} | Recency Dev: {dev_r:.4f} (Imp: {((dev_b-dev_r)/dev_b)*100:+.2f}%)")

# ==========================================
# 5. GOALS VS PROCESS STATS (xG/90 vs Goals/90)
# ==========================================
print("\n--- 5. GOALS VS PROCESS STATS ---")
corr_xg_future_xg = test_df['xg_90_5'].corr(test_df['target_xg'])
corr_goals_future_xg = test_df['goals_90_5'].corr(test_df['target_xg'])
print(f"Correlation of xG/90_last_5 with Future xG: {corr_xg_future_xg:.4f}")
print(f"Correlation of Goals/90_last_5 with Future xG: {corr_goals_future_xg:.4f}")

# ==========================================
# 6. REGRESSION TO THE MEAN AUDIT
# ==========================================
print("\n--- 6. REGRESSION TO THE MEAN AUDIT ---")
spikers = test_df[test_df['xg_90_3'] >= 0.70]
print(f"Matches where player had xG/90_last_3 >= 0.70: N={len(spikers)}")
print(f"Mean xG/90 in spike window (last 3): {spikers['xg_90_3'].mean():.3f}")
print(f"Mean actual xG in subsequent target match: {spikers['target_xg'].mean():.3f}")
print(f"Mean career xG/90 of spikers: {spikers['xg_90_career'].mean():.3f}")
print(f"Regressed rate (Actual / 3-match rate): {spikers['target_xg'].mean() / (spikers['xg_90_3'].mean()/90 * 80):.2%}")

# Save JSON results for summary report
output_summary = {
    "mins": {"mae_base": mae_mins_base, "mae_rec": mae_mins_rec, "imp_mae": ((mae_mins_base - mae_mins_rec)/mae_mins_base)*100, "brier_base": brier_start_base, "brier_rec": brier_start_rec, "imp_brier": ((brier_start_base - brier_start_rec)/brier_start_base)*100},
    "xg": xg_results,
    "xa": xa_results
}

with open("scratch/phase3c7_audit_output.json", "w") as f:
    json.dump(output_summary, f, indent=2)

print("\nAudit analysis completed successfully. Serialized to scratch/phase3c7_audit_output.json")
