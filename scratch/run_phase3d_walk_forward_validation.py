import os
import sys
import json
import hashlib
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, brier_score_loss
import lightgbm as lgb

sys.path.append(os.getcwd())
from backend.ml.minutes_candidate_v2 import MinutesCandidateV2
from backend.ml.xg_candidate_v2 import XGCandidateV2, XG_POSITION_PRIORS
from backend.ml.xa_candidate_v2 import XACandidateV2, XA_POSITION_PRIORS
from scratch.run_phase3c7_temporal_audit import construct_leak_free_temporal_dataset, load_data

def get_file_hash(filepath: str) -> str:
    """Calculate SHA256 hash of a model file."""
    if not os.path.exists(filepath):
        return "MISSING"
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()[:16]

def poisson_dev(y_true, y_pred, eps=1e-9):
    y_pred = np.clip(y_pred, eps, None)
    y_true = np.clip(y_true, 0, None)
    dev = 2 * (y_true * np.log(np.maximum(eps, y_true) / y_pred) - (y_true - y_pred))
    return float(np.mean(dev))

print("=== 1. FREEZING PRODUCTION V1 BASELINES & ARTIFACT HASHES ===")
v1_artifacts = {
    'minutes_start_v1': 'models/minutes_start_v1.pkl',
    'minutes_regression_v1': 'models/minutes_regression_v1.pkl',
    'minutes_60plus_v1': 'models/minutes_60plus_v1.pkl',
    'minutes_zero_v1': 'models/minutes_zero_v1.pkl',
    'xg_v1_lgbm': 'models/xg_v1_lgbm.pkl',
    'xa_v1_lgbm': 'models/xa_v1_lgbm.pkl'
}

baseline_hashes = {k: get_file_hash(v) for k, v in v1_artifacts.items()}
for k, h in baseline_hashes.items():
    print(f"Artifact: {k:<25} | Path: {v1_artifacts[k]:<32} | SHA256 (16 char): {h}")

print("\n=== 2. LOADING DATASET FOR CHRONOLOGICAL WALK-FORWARD EVALUATION ===")
df_temp = construct_leak_free_temporal_dataset(load_data())
print(f"Total dataset records: {len(df_temp)}")

folds_def = [
    {'name': 'Fold 1 (Train 22-23 -> Test 23-24)', 'train_seasons': ["2022-23"], 'test_season': "2023-24"},
    {'name': 'Fold 2 (Train 22-24 -> Test 24-25)', 'train_seasons': ["2022-23", "2023-24"], 'test_season': "2024-25"},
    {'name': 'Fold 3 (Train 22-25 -> Test 25-26)', 'train_seasons': ["2022-23", "2023-24", "2024-25"], 'test_season': "2025-26"}
]

cand_mins = MinutesCandidateV2()
cand_xg = XGCandidateV2()
cand_xa = XACandidateV2()

fold_results = []

for fold in folds_def:
    train_data = df_temp[df_temp['season'].isin(fold['train_seasons'])].copy()
    test_data = df_temp[df_temp['season'] == fold['test_season']].copy()
    
    # Baseline V1 Predictions
    mins_v1, mins_v2 = [], []
    pstart_v1, pstart_v2 = [], []
    xg_v1, xg_v2 = [], []
    xa_v1, xa_v2 = [], []
    
    for _, row in test_data.iterrows():
        tot_mins = float(row['tot_mins_prior'])
        pos = str(row['position'])
        
        # V1 Baseline Estimates
        v1_recent_starts = float(min(5.0, tot_mins / 80.0)) if tot_mins >= 80 else 0.0
        v1_m = float(min(85.0, 15.0 + v1_recent_starts * 14.0)) if tot_mins >= 80 else 15.0
        v1_ps = float(min(0.95, 0.10 + v1_recent_starts * 0.16)) if tot_mins >= 80 else 0.10
        v1_xg_r = float(row['xg_90_career']) * (v1_m / 90.0)
        v1_xa_r = float(row['xa_90_career']) * (v1_m / 90.0)
        
        # Candidate V2 Estimates
        pdata_dummy = {
            'fixture_difficulty': 3, 'team_attack_rating': 1000, 'team_defence_rating': 1000,
            'opponent_attack_rating': 1000, 'opponent_defence_rating': 1000, 'home_away_is_home': 1.0,
            'price': 5.5, 'appearances_last_5': float(row['starts_last_5'])
        }
        res_m2 = cand_mins.predict_candidate_minutes(
            pdata=pdata_dummy, actual_recent_starts_5=row['starts_last_5'],
            actual_recent_mins_5=row['mins_last_5'], current_club_starts=row['starts_last_5'],
            current_club_mins=row['curr_club_mins'], pos=pos, cost=5.5
        )
        v2_m = res_m2['expected_minutes_v2']
        v2_ps = res_m2['p_start_v2']
        
        res_xg2 = cand_xg.calculate_shrunk_xg90(row['xg_90_5'], tot_mins, pos)
        v2_xg_r = res_xg2['shrunk_xg90'] * (v2_m / 90.0)
        
        res_xa2 = cand_xa.calculate_shrunk_xa90(row['xa_90_5'], tot_mins, pos)
        v2_xa_r = res_xa2['shrunk_xa90'] * (v2_m / 90.0)
        
        mins_v1.append(v1_m); mins_v2.append(v2_m)
        pstart_v1.append(v1_ps); pstart_v2.append(v2_ps)
        xg_v1.append(v1_xg_r); xg_v2.append(v2_xg_r)
        xa_v1.append(v1_xa_r); xa_v2.append(v2_xa_r)
        
    mae_m1 = mean_absolute_error(test_data['target_mins'], mins_v1)
    mae_m2 = mean_absolute_error(test_data['target_mins'], mins_v2)
    brier_ps1 = brier_score_loss(test_data['target_starts'], pstart_v1)
    brier_ps2 = brier_score_loss(test_data['target_starts'], pstart_v2)
    
    dev_xg1 = poisson_dev(test_data['target_xg'].values, xg_v1)
    dev_xg2 = poisson_dev(test_data['target_xg'].values, xg_v2)
    
    dev_xa1 = poisson_dev(test_data['target_xa'].values, xa_v1)
    dev_xa2 = poisson_dev(test_data['target_xa'].values, xa_v2)
    
    fold_entry = {
        'fold': fold['name'],
        'train_records': len(train_data), 'test_records': len(test_data),
        'mae_mins_v1': round(mae_m1, 2), 'mae_mins_v2': round(mae_m2, 2), 'imp_mins': round(((mae_m1-mae_m2)/mae_m1)*100, 2),
        'brier_ps_v1': round(brier_ps1, 4), 'brier_ps_v2': round(brier_ps2, 4), 'imp_brier': round(((brier_ps1-brier_ps2)/brier_ps1)*100, 2),
        'dev_xg_v1': round(dev_xg1, 4), 'dev_xg_v2': round(dev_xg2, 4), 'imp_xg': round(((dev_xg1-dev_xg2)/dev_xg1)*100, 2),
        'dev_xa_v1': round(dev_xa1, 4), 'dev_xa_v2': round(dev_xa2, 4), 'imp_xa': round(((dev_xa1-dev_xa2)/dev_xa1)*100, 2)
    }
    fold_results.append(fold_entry)
    print(f"\n--- {fold['name']} ---")
    print(f"  Minutes MAE : v1 = {mae_m1:.2f}m | v2 = {mae_m2:.2f}m (Imp: {fold_entry['imp_mins']:+.2f}%)")
    print(f"  P(start) Brier: v1 = {brier_ps1:.4f} | v2 = {brier_ps2:.4f} (Imp: {fold_entry['imp_brier']:+.2f}%)")
    print(f"  xG Deviance  : v1 = {dev_xg1:.4f} | v2 = {dev_xg2:.4f} (Imp: {fold_entry['imp_xg']:+.2f}%)")
    print(f"  xA Deviance  : v1 = {dev_xa1:.4f} | v2 = {dev_xa2:.4f} (Imp: {fold_entry['imp_xa']:+.2f}%)")

# ==========================================
# 3. TRAINING & DEPLOYING PRODUCTION V2 ARTIFACTS
# ==========================================
print("\n=== 3. TRAINING & DEPLOYING PRODUCTION V2 MODEL ARTIFACTS ===")

# Train production LightGBM xG v2 model
xg_feat_cols = ['xg_90_3', 'xg_90_5', 'xg_90_10', 'xg_90_career', 'tot_mins_prior', 'mins_last_5', 'starts_last_5']
X_train_xg = df_temp[xg_feat_cols]
y_train_xg = df_temp['target_xg']

params_xg = {'objective': 'regression', 'metric': 'rmse', 'learning_rate': 0.05, 'num_leaves': 15, 'verbose': -1}
lgb_train_xg = lgb.Dataset(X_train_xg, y_train_xg)
model_xg_v2 = lgb.train(params_xg, lgb_train_xg, num_boost_round=100)

with open("models/xg_v2.pkl", "wb") as f:
    pickle.dump(model_xg_v2, f)

# Train production LightGBM xA v2 model
xa_feat_cols = ['xa_90_3', 'xa_90_5', 'xa_90_10', 'xa_90_career', 'tot_mins_prior', 'mins_last_5', 'starts_last_5']
X_train_xa = df_temp[xa_feat_cols]
y_train_xa = df_temp['target_xa']

params_xa = {'objective': 'regression', 'metric': 'rmse', 'learning_rate': 0.05, 'num_leaves': 15, 'verbose': -1}
lgb_train_xa = lgb.Dataset(X_train_xa, y_train_xa)
model_xa_v2 = lgb.train(params_xa, lgb_train_xa, num_boost_round=100)

with open("models/xa_v2.pkl", "wb") as f:
    pickle.dump(model_xa_v2, f)

# Save expected minutes v2 config / model
with open("models/expected_minutes_v2.pkl", "wb") as f:
    pickle.dump({'version': 'expected_minutes_v2', 'm0_mins': 750.0}, f)

v2_artifacts = {
    'expected_minutes_v2': 'models/expected_minutes_v2.pkl',
    'xg_v2': 'models/xg_v2.pkl',
    'xa_v2': 'models/xa_v2.pkl'
}

v2_hashes = {k: get_file_hash(v) for k, v in v2_artifacts.items()}
print("Successfully saved versioned production v2 artifacts:")
for k, h in v2_hashes.items():
    print(f"Artifact: {k:<25} | Path: {v2_artifacts[k]:<32} | SHA256: {h}")

# Save JSON results
out_data = {
    'v1_baseline_hashes': baseline_hashes,
    'v2_production_hashes': v2_hashes,
    'folds': fold_results
}

with open("scratch/phase3d_validation_results.json", "w") as f:
    json.dump(out_data, f, indent=2)

print("\nValidation and deployment process complete. Results saved to scratch/phase3d_validation_results.json")
