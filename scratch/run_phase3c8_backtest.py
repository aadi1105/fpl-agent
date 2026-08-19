import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, brier_score_loss

sys.path.append(os.getcwd())
from backend.ml.minutes_candidate_v2 import MinutesCandidateV2
from backend.ml.xg_candidate_v2 import XGCandidateV2
from backend.ml.xa_candidate_v2 import XACandidateV2
from scratch.run_phase3c7_temporal_audit import construct_leak_free_temporal_dataset, load_data

def poisson_dev(y_true, y_pred, eps=1e-9):
    y_pred = np.clip(y_pred, eps, None)
    y_true = np.clip(y_true, 0, None)
    dev = 2 * (y_true * np.log(np.maximum(eps, y_true) / y_pred) - (y_true - y_pred))
    return float(np.mean(dev))

print("Loading raw data and building leak-free dataset...")
df_temp = construct_leak_free_temporal_dataset(load_data())

train_df = df_temp[df_temp['season'].isin(["2022-23", "2023-24", "2024-25"])].copy()
test_df = df_temp[df_temp['season'] == "2025-26"].copy()

print(f"Train records (2022-25): {len(train_df)} | Test records (2025-26): {len(test_df)}")

# Instantiate Candidate V2 Predictors
cand_mins = MinutesCandidateV2()
cand_xg = XGCandidateV2()
cand_xa = XACandidateV2()

# Run Candidate V2 Predictions on Test Set
mins_v1 = []
mins_v2 = []
pstart_v1 = []
pstart_v2 = []

xg90_v1 = []
xg90_v2 = []
match_xg_v1 = []
match_xg_v2 = []

xa90_v1 = []
xa90_v2 = []
match_xa_v1 = []
match_xa_v2 = []

xp_v1 = []
xp_v2 = []

for idx, row in test_df.iterrows():
    # V1 Un-shrunk Estimates (Baseline)
    tot_mins = float(row['tot_mins_prior'])
    pos = str(row['position'])
    
    # Baseline V1 synthetic recent starts & un-shrunk rates
    v1_recent_starts = float(min(5.0, tot_mins / 80.0)) if tot_mins >= 80 else 0.0
    v1_mins = float(min(85.0, 15.0 + v1_recent_starts * 14.0)) if tot_mins >= 80 else 15.0
    v1_pstart = float(min(0.95, 0.10 + v1_recent_starts * 0.16)) if tot_mins >= 80 else 0.10
    
    v1_xg90 = float(row['xg_90_career'])
    v1_xa90 = float(row['xa_90_career'])
    
    v1_match_xg = v1_xg90 * (v1_mins / 90.0)
    v1_match_xa = v1_xa90 * (v1_mins / 90.0)
    v1_total_xp = (v1_mins / 90.0 * 2.0) + (v1_match_xg * 4.0) + (v1_match_xa * 3.0)
    
    # Candidate V2 Estimates (Fixed starts + Bayesian shrinkage)
    pdata_dummy = {
        'fixture_difficulty': 3, 'team_attack_rating': 1000, 'team_defence_rating': 1000,
        'opponent_attack_rating': 1000, 'opponent_defence_rating': 1000, 'home_away_is_home': 1.0,
        'price': 5.5, 'appearances_last_5': float(row['starts_last_5'])
    }
    
    res_mins_v2 = cand_mins.predict_candidate_minutes(
        pdata=pdata_dummy,
        actual_recent_starts_5=row['starts_last_5'],
        actual_recent_mins_5=row['mins_last_5'],
        current_club_starts=row['starts_last_5'],
        current_club_mins=row['curr_club_mins'],
        pos=pos,
        cost=5.5
    )
    v2_mins = res_mins_v2['expected_minutes_v2']
    v2_pstart = res_mins_v2['p_start_v2']
    
    # Candidate V2 xG & xA Shrinkage
    res_xg_v2 = cand_xg.calculate_shrunk_xg90(row['xg_90_5'], tot_mins, pos)
    v2_xg90 = res_xg_v2['shrunk_xg90']
    
    res_xa_v2 = cand_xa.calculate_shrunk_xa90(row['xa_90_5'], tot_mins, pos)
    v2_xa90 = res_xa_v2['shrunk_xa90']
    
    v2_match_xg = v2_xg90 * (v2_mins / 90.0)
    v2_match_xa = v2_xa90 * (v2_mins / 90.0)
    v2_total_xp = (v2_mins / 90.0 * 2.0) + (v2_match_xg * 4.0) + (v2_match_xa * 3.0)
    
    mins_v1.append(v1_mins)
    mins_v2.append(v2_mins)
    pstart_v1.append(v1_pstart)
    pstart_v2.append(v2_pstart)
    
    xg90_v1.append(v1_xg90)
    xg90_v2.append(v2_xg90)
    match_xg_v1.append(v1_match_xg)
    match_xg_v2.append(v2_match_xg)
    
    xa90_v1.append(v1_xa90)
    xa90_v2.append(v2_xa90)
    match_xa_v1.append(v1_match_xa)
    match_xa_v2.append(v2_match_xa)
    
    xp_v1.append(v1_total_xp)
    xp_v2.append(v2_total_xp)

test_df['mins_v1'] = mins_v1
test_df['mins_v2'] = mins_v2
test_df['pstart_v1'] = pstart_v1
test_df['pstart_v2'] = pstart_v2
test_df['match_xg_v1'] = match_xg_v1
test_df['match_xg_v2'] = match_xg_v2
test_df['match_xa_v1'] = match_xa_v1
test_df['match_xa_v2'] = match_xa_v2

# ==========================================
# EVALUATION METRICS
# ==========================================
print("\n=== OUT-OF-SAMPLE EVALUATION: V1 BASELINE VS CANDIDATE V2 ===")

# Minutes Evaluation
mae_m1 = mean_absolute_error(test_df['target_mins'], mins_v1)
mae_m2 = mean_absolute_error(test_df['target_mins'], mins_v2)
rmse_m1 = np.sqrt(mean_squared_error(test_df['target_mins'], mins_v1))
rmse_m2 = np.sqrt(mean_squared_error(test_df['target_mins'], mins_v2))
brier_s1 = brier_score_loss(test_df['target_starts'], pstart_v1)
brier_s2 = brier_score_loss(test_df['target_starts'], pstart_v2)

print(f"Expected Minutes MAE : V1 Baseline = {mae_m1:.2f}m | Candidate V2 = {mae_m2:.2f}m (Imp: {((mae_m1-mae_m2)/mae_m1)*100:+.2f}%)")
print(f"Expected Minutes RMSE: V1 Baseline = {rmse_m1:.2f}  | Candidate V2 = {rmse_m2:.2f}  (Imp: {((rmse_m1-rmse_m2)/rmse_m1)*100:+.2f}%)")
print(f"P(start) Brier Score : V1 Baseline = {brier_s1:.4f} | Candidate V2 = {brier_s2:.4f} (Imp: {((brier_s1-brier_s2)/brier_s1)*100:+.2f}%)")

# xG Evaluation
dev_xg1 = poisson_dev(test_df['target_xg'].values, match_xg_v1)
dev_xg2 = poisson_dev(test_df['target_xg'].values, match_xg_v2)
mae_xg1 = mean_absolute_error(test_df['target_xg'], match_xg_v1)
mae_xg2 = mean_absolute_error(test_df['target_xg'], match_xg_v2)

print(f"Match xG Deviance    : V1 Baseline = {dev_xg1:.4f} | Candidate V2 = {dev_xg2:.4f} (Imp: {((dev_xg1-dev_xg2)/dev_xg1)*100:+.2f}%)")
print(f"Match xG MAE         : V1 Baseline = {mae_xg1:.4f} | Candidate V2 = {mae_xg2:.4f} (Imp: {((mae_xg1-mae_xg2)/mae_xg1)*100:+.2f}%)")

# xA Evaluation
dev_xa1 = poisson_dev(test_df['target_xa'].values, match_xa_v1)
dev_xa2 = poisson_dev(test_df['target_xa'].values, match_xa_v2)
mae_xa1 = mean_absolute_error(test_df['target_xa'], match_xa_v1)
mae_xa2 = mean_absolute_error(test_df['target_xa'], match_xa_v2)

print(f"Match xA Deviance    : V1 Baseline = {dev_xa1:.4f} | Candidate V2 = {dev_xa2:.4f} (Imp: {((dev_xa1-dev_xa2)/dev_xa1)*100:+.2f}%)")
print(f"Match xA MAE         : V1 Baseline = {mae_xa1:.4f} | Candidate V2 = {mae_xa2:.4f} (Imp: {((mae_xa1-mae_xa2)/mae_xa1)*100:+.2f}%)")

# ==========================================
# DIAGNOSTIC TARGET PLAYER COMPARISON
# ==========================================
target_players = ["Taiwo Awoniyi", "William Osula", "Beto", "Omar Marmoush", "Erling Haaland", "Alexander Isak", "Dominic Solanke", "João Pedro", "Dominic Calvert-Lewin"]

print("\n=== DIAGNOSTIC PLAYER COMPARISON (V1 vs CANDIDATE V2) ===")
player_comp = []
for p_name in target_players:
    sub = test_df[test_df['player_name'].str.contains(p_name, case=False, na=False)]
    if len(sub) > 0:
        row = sub.iloc[-1]
        p_pos = str(row['position'])
        tot_m = float(row['tot_mins_prior'])
        
        # Calculate V1 & V2 for latest fixture
        v1_m = float(row['mins_v1'])
        v2_m = float(row['mins_v2'])
        
        v1_ps = float(row['pstart_v1'])
        v2_ps = float(row['pstart_v2'])
        
        res_xg = cand_xg.calculate_shrunk_xg90(row['xg_90_5'], tot_m, p_pos)
        v1_xg_r = float(row['xg_90_career'])
        v2_xg_r = res_xg['shrunk_xg90']
        
        res_xa = cand_xa.calculate_shrunk_xa90(row['xa_90_5'], tot_m, p_pos)
        v1_xa_r = float(row['xa_90_career'])
        v2_xa_r = res_xa['shrunk_xa90']
        
        v1_xp_val = round((v1_m/90.0*2.0) + (v1_xg_r * v1_m/90.0 * 4.0) + (v1_xa_r * v1_m/90.0 * 3.0), 2)
        v2_xp_val = round((v2_m/90.0*2.0) + (v2_xg_r * v2_m/90.0 * 4.0) + (v2_xa_r * v2_m/90.0 * 3.0), 2)
        
        p_entry = {
            'player_name': row['player_name'],
            'tot_mins_prior': tot_m,
            'position': p_pos,
            'v1_mins': v1_m, 'v2_mins': v2_m,
            'v1_pstart': v1_ps, 'v2_pstart': v2_ps,
            'v1_xg90': v1_xg_r, 'v2_xg90': v2_xg_r,
            'v1_xa90': v1_xa_r, 'v2_xa90': v2_xa_r,
            'v1_xp': v1_xp_val, 'v2_xp': v2_xp_val,
            'w_xg': res_xg['w_evidence'],
            'w_xa': res_xa['w_evidence']
        }
        player_comp.append(p_entry)
        print(f"--- {p_entry['player_name']} (Prior Mins: {tot_m:.0f}) ---")
        print(f"  xMins : V1 = {v1_m:.1f}m | V2 = {v2_m:.1f}m")
        print(f"  P(start): V1 = {v1_ps*100:.1f}% | V2 = {v2_ps*100:.1f}%")
        print(f"  xG/90 : V1 = {v1_xg_r:.3f} | V2 = {v2_xg_r:.3f} (Shrink weight w={res_xg['w_evidence']:.2f})")
        print(f"  xA/90 : V1 = {v1_xa_r:.3f} | V2 = {v2_xa_r:.3f} (Shrink weight w={res_xa['w_evidence']:.2f})")
        print(f"  xP    : V1 = {v1_xp_val:.2f} | V2 = {v2_xp_val:.2f}")

# Serialize results to JSON
out_json = {
    'metrics': {
        'mae_mins_v1': mae_m1, 'mae_mins_v2': mae_m2, 'imp_mae_mins': ((mae_m1-mae_m2)/mae_m1)*100,
        'brier_start_v1': brier_s1, 'brier_start_v2': brier_s2, 'imp_brier_start': ((brier_s1-brier_s2)/brier_s1)*100,
        'dev_xg_v1': dev_xg1, 'dev_xg_v2': dev_xg2, 'imp_dev_xg': ((dev_xg1-dev_xg2)/dev_xg1)*100,
        'dev_xa_v1': dev_xa1, 'dev_xa_v2': dev_xa2, 'imp_dev_xa': ((dev_xa1-dev_xa2)/dev_xa1)*100
    },
    'players': player_comp
}

with open("scratch/phase3c8_backtest_output.json", "w") as f:
    json.dump(out_json, f, indent=2)

print("\nBacktest completed successfully. Serialized to scratch/phase3c8_backtest_output.json")
