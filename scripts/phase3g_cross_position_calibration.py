import os
import sys
import json
import math
import logging
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, brier_score_loss

sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models import Player, Fixture, Team
from backend.projections.engine import ProjectionEngine
from backend.ml.minutes_predictor import MinutesPredictor
from backend.ml.xg_predictor import XGPredictor
from backend.ml.xa_predictor import XAPredictor
from backend.ml.cs_predictor import CSPredictor
from backend.ml.defcon_predictor import DEFCONPredictor

RAW_FILES = {
    "2022-23": "data/raw/merged_gw_2022-23.csv",
    "2023-24": "data/raw/merged_gw_2023-24.csv",
    "2024-25": "data/raw/merged_gw_2024-25.csv",
    "2025-26": "data/raw/merged_gw_2025-26.csv"
}

def load_historical_data():
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
    
    for col in ['minutes', 'starts', 'goals_scored', 'assists', 'expected_goals', 'expected_assists', 
                'total_points', 'value', 'clean_sheets']:
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0.0)
            
    season_order = {"2022-23": 1, "2023-24": 2, "2024-25": 3, "2025-26": 4}
    df_raw['season_idx'] = df_raw['season'].map(season_order)
    df_raw = df_raw.sort_values(by=['season_idx', 'gameweek', 'player_id']).reset_index(drop=True)
    return df_raw

def construct_eval_dataset(df_raw):
    mins_pred = MinutesPredictor()
    xg_pred = XGPredictor()
    xa_pred = XAPredictor()

    print("Generating leak-free pre-deadline features across observations...")
    
    grouped = df_raw.groupby('player_id', group_keys=False)

    def build_player_rolling(g):
        g = g.sort_values(by=['season_idx', 'gameweek'])
        n = len(g)
        mins = g['minutes'].values
        starts = g['starts'].values
        xg = g['expected_goals'].values
        xa = g['expected_assists'].values
        
        mins_shift = np.zeros(n)
        starts_shift = np.zeros(n)
        xg_shift = np.zeros(n)
        xa_shift = np.zeros(n)

        mins_shift[1:] = mins[:-1]
        starts_shift[1:] = starts[:-1]
        xg_shift[1:] = xg[:-1]
        xa_shift[1:] = xa[:-1]

        def rolling_sum(arr, window):
            res = np.zeros(n)
            for i in range(n):
                start_i = max(0, i - window)
                res[i] = np.sum(arr[start_i:i])
            return res

        g['mins_last_5'] = rolling_sum(mins_shift, 5)
        g['starts_last_5'] = rolling_sum(starts_shift, 5)
        g['xg_last_5'] = rolling_sum(xg_shift, 5)
        g['xa_last_5'] = rolling_sum(xa_shift, 5)
        g['tot_mins_prior'] = rolling_sum(mins_shift, 38)
        return g

    df_feats = grouped.apply(build_player_rolling)
    
    pos_map = {"GK": "GKP", "GKP": "GKP", "DEF": "DEF", "MID": "MID", "FWD": "FWD"}
    if 'position' in df_feats.columns:
        df_feats['position'] = df_feats['position'].map(lambda x: pos_map.get(str(x).upper(), "MID"))
    elif 'element_type' in df_feats.columns:
        type_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
        df_feats['position'] = df_feats['element_type'].map(lambda x: type_map.get(x, "MID"))

    # Filter active observations (players with minutes > 0 or in squad)
    df_eval = df_feats[df_feats['mins_last_5'] > 0].copy().reset_index(drop=True)

    # Vectorized Minutes Inference via batch
    df_mins_input = pd.DataFrame()
    df_mins_input['price'] = df_eval['value'] / 10.0 if 'value' in df_eval.columns else 6.0
    df_mins_input['fixture_difficulty'] = 3.0
    df_mins_input['team_attack_rating'] = 1000.0
    df_mins_input['team_defence_rating'] = 1000.0
    df_mins_input['opponent_attack_rating'] = 1000.0
    df_mins_input['opponent_defence_rating'] = 1000.0
    df_mins_input['home_away_is_home'] = (df_eval['was_home'] == True).astype(float) if 'was_home' in df_eval.columns else 1.0

    df_mins_input['minutes_last_1'] = np.minimum(90.0, df_eval['mins_last_5'])
    df_mins_input['minutes_last_3'] = np.minimum(270.0, df_eval['mins_last_5'])
    df_mins_input['minutes_last_5'] = df_eval['mins_last_5']
    df_mins_input['minutes_last_10'] = df_eval['mins_last_5'] * 2.0
    df_mins_input['starts_last_1'] = np.where(df_eval['starts_last_5'] > 0, 1.0, 0.0)
    df_mins_input['starts_last_3'] = np.minimum(3.0, df_eval['starts_last_5'])
    df_mins_input['starts_last_5'] = df_eval['starts_last_5']
    df_mins_input['starts_last_10'] = df_eval['starts_last_5'] * 2.0
    df_mins_input['appearances_last_5'] = (df_eval['mins_last_5'] / 60.0).clip(0, 5)
    df_mins_input['bench_appearances_last_5'] = 0.0
    df_mins_input['unused_substitute_last_5'] = 0.0
    df_mins_input['average_minutes_last_5'] = df_eval['mins_last_5'] / np.maximum(1.0, df_eval['mins_last_5'] / 60.0)
    df_mins_input['average_minutes_last_10'] = df_eval['mins_last_5'] / np.maximum(1.0, df_eval['mins_last_5'] / 60.0)
    df_mins_input['days_since_last_match'] = 7.0
    df_mins_input['matches_in_previous_14_days'] = 2.0
    df_mins_input['matches_in_previous_21_days'] = 3.0
    df_mins_input['fixture_congestion'] = 0.0
    df_mins_input['pos_DEF'] = (df_eval['position'] == 'DEF').astype(float)
    df_mins_input['pos_MID'] = (df_eval['position'] == 'MID').astype(float)
    df_mins_input['pos_FWD'] = (df_eval['position'] == 'FWD').astype(float)

    df_mins_res = mins_pred.predict_batch(df_mins_input)
    df_eval['pred_xMins'] = df_mins_res['expected_minutes_v1']
    df_eval['p_start'] = df_mins_res['p_start']

    # Vectorized xG & xA Model Inference
    print("Computing vectorized xG & xA model inference...")
    df_eval['xg_per_90_last_5'] = (df_eval['xg_last_5'] / np.maximum(1.0, df_eval['mins_last_5'])) * 90.0
    df_eval['xa_per_90_last_5'] = (df_eval['xa_last_5'] / np.maximum(1.0, df_eval['mins_last_5'])) * 90.0

    xg90 = df_eval['xg_per_90_last_5'].values
    xa90 = df_eval['xa_per_90_last_5'].values

    # Construct feature DataFrames for model inference
    df_xg_feat = pd.DataFrame({
        "xg_90_3": xg90,
        "xg_90_5": xg90,
        "xg_90_10": xg90,
        "xg_90_career": xg90,
        "tot_mins_prior": df_eval['tot_mins_prior'].values,
        "mins_last_5": df_eval['mins_last_5'].values,
        "starts_last_5": df_eval['starts_last_5'].values
    })

    df_xa_feat = pd.DataFrame({
        "xa_90_3": xa90,
        "xa_90_5": xa90,
        "xa_90_10": xa90,
        "xa_90_career": xa90,
        "tot_mins_prior": df_eval['tot_mins_prior'].values,
        "mins_last_5": df_eval['mins_last_5'].values,
        "starts_last_5": df_eval['starts_last_5'].values
    })

    if xg_pred.is_loaded:
        df_eval['pred_xG'] = np.clip(xg_pred.model.predict(df_xg_feat), 0.0, 3.0)
    else:
        df_eval['pred_xG'] = xg90 * (df_eval['pred_xMins'].values / 90.0)

    if xa_pred.is_loaded:
        df_eval['pred_xA'] = np.clip(xa_pred.model.predict(df_xa_feat), 0.0, 3.0)
    else:
        df_eval['pred_xA'] = xa90 * (df_eval['pred_xMins'].values / 90.0)

    # CS Probability Inference (Home vs Away baseline modifier)
    is_home = (df_eval['was_home'] == True).values if 'was_home' in df_eval.columns else np.ones(len(df_eval), dtype=bool)
    df_eval['pred_CS_prob'] = np.where(is_home, 0.410, 0.280)

    # DEFCON Inference (Position based: DEF get ~0.14, GKP ~0.10, MID ~0.02, FWD ~0.0)
    pos_defcon_map = {"DEF": 0.14, "GKP": 0.10, "MID": 0.02, "FWD": 0.00}
    df_eval['pred_DEFCON_prob'] = df_eval['position'].map(pos_defcon_map).fillna(0.0)

    # Calculate Component Expected Points (FPL Scoring Rules)
    xMins = df_eval['pred_xMins'].values
    pos = df_eval['position'].values
    
    goal_mult = np.where(pos == 'DEF', 6.0, np.where(pos == 'GKP', 6.0, np.where(pos == 'MID', 5.0, 4.0)))
    cs_mult = np.where(pos == 'DEF', 4.0, np.where(pos == 'GKP', 4.0, np.where(pos == 'MID', 1.0, 0.0)))
    
    goals_xp = df_eval['pred_xG'].values * goal_mult * (xMins / 90.0)
    assists_xp = df_eval['pred_xA'].values * 3.0 * (xMins / 90.0)
    cs_xp = df_eval['pred_CS_prob'].values * cs_mult * (xMins / 90.0)
    defcon_xp = df_eval['pred_DEFCON_prob'].values * 2.0 * (xMins / 90.0)
    app_xp = np.where(xMins >= 60.0, 2.0 * (df_eval['p_start'].values), np.where(xMins > 0.0, 1.0 * (df_eval['p_start'].values), 0.0))
    bonus_xp = (goals_xp * 0.4) + (assists_xp * 0.3)
    cards_xp = np.where(xMins > 0.0, -0.09, 0.0)

    df_eval['pred_xP'] = np.round(app_xp + goals_xp + assists_xp + cs_xp + defcon_xp + bonus_xp + cards_xp, 2)
    df_eval['actual_points'] = df_eval['total_points']
    df_eval['actual_goals'] = df_eval['goals_scored']
    df_eval['actual_assists'] = df_eval['assists']
    df_eval['actual_cs'] = df_eval['clean_sheets'] if 'clean_sheets' in df_eval.columns else 0.0

    return df_eval

def run_phase3g_audit():
    print("==================================================")
    print("PHASE 3G — CROSS-POSITION xP CALIBRATION & VALUE AUDIT")
    print("==================================================\n")

    df_raw = load_historical_data()
    print(f"Loaded {len(df_raw)} historical player-gameweek observations across 4 seasons.\n")
    df_eval = construct_eval_dataset(df_raw)
    print(f"Processed {len(df_eval)} active historical evaluation observations.\n")

    # ----------------------------------------------------
    # SECTION 3: EVALUATE xP CALIBRATION BY POSITION
    # ----------------------------------------------------
    print("==================================================")
    print("SECTION 3: EVALUATE xP CALIBRATION BY POSITION")
    print("==================================================")
    pos_table = []
    for p in ["GKP", "DEF", "MID", "FWD"]:
        sub = df_eval[df_eval['position'] == p]
        pred_m = sub['pred_xP'].mean()
        act_m = sub['actual_points'].mean()
        bias = act_m - pred_m
        mae = mean_absolute_error(sub['actual_points'], sub['pred_xP'])
        rmse = np.sqrt(mean_squared_error(sub['actual_points'], sub['pred_xP']))
        med_err = np.median(sub['actual_points'] - sub['pred_xP'])
        sp, _ = spearmanr(sub['pred_xP'], sub['actual_points'])
        pe, _ = pearsonr(sub['pred_xP'], sub['actual_points'])

        pos_table.append({
            "position": p,
            "count": len(sub),
            "pred_mean": round(pred_m, 2),
            "act_mean": round(act_m, 2),
            "bias": round(bias, 2),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "median_err": round(med_err, 2),
            "spearman": round(sp, 4),
            "pearson": round(pe, 4)
        })

    print(f"{'Position':<8} | {'Obs':<7} | {'Pred Mean':<10} | {'Act Mean':<9} | {'Bias (Act-Pred)':<15} | {'MAE':<6} | {'RMSE':<6} | {'Spearman':<10}")
    print("-" * 85)
    for r in pos_table:
        print(f"{r['position']:<8} | {r['count']:<7} | {r['pred_mean']:<10.2f} | {r['act_mean']:<9.2f} | {r['bias']:<15.2f} | {r['mae']:<6.2f} | {r['rmse']:<6.2f} | {r['spearman']:<10.4f}")
    print()

    # ----------------------------------------------------
    # SECTION 4: EVALUATE BY PREDICTED xP BUCKET
    # ----------------------------------------------------
    print("==================================================")
    print("SECTION 4: EVALUATE BY PREDICTED xP BUCKET")
    print("==================================================")
    bins = [0, 2, 3, 4, 5, 6, 7, 8, 100]
    labels = ["0-2", "2-3", "3-4", "4-5", "5-6", "6-7", "7-8", "8+"]
    df_eval['xp_bucket'] = pd.cut(df_eval['pred_xP'], bins=bins, labels=labels, right=False)

    bucket_table = []
    for b in labels:
        sub = df_eval[df_eval['xp_bucket'] == b]
        if len(sub) == 0:
            continue
        p_m = sub['pred_xP'].mean()
        a_m = sub['actual_points'].mean()
        b_bias = a_m - p_m
        b_mae = mean_absolute_error(sub['actual_points'], sub['pred_xP'])
        bucket_table.append({
            "bucket": b,
            "count": len(sub),
            "pred_mean": round(p_m, 2),
            "act_mean": round(a_m, 2),
            "bias": round(b_bias, 2),
            "mae": round(b_mae, 2)
        })
    print(f"{'Bucket':<8} | {'Count':<7} | {'Pred Mean':<10} | {'Act Mean':<9} | {'Bias (Act-Pred)':<15} | {'MAE':<6}")
    print("-" * 65)
    for r in bucket_table:
        print(f"{r['bucket']:<8} | {r['count']:<7} | {r['pred_mean']:<10.2f} | {r['act_mean']:<9.2f} | {r['bias']:<15.2f} | {r['mae']:<6.2f}")
    print()

    # ----------------------------------------------------
    # SECTION 5: CROSS-POSITION MATCHED COHORT COMPARISON
    # ----------------------------------------------------
    print("==================================================")
    print("SECTION 5: CROSS-POSITION MATCHED COHORT COMPARISON")
    print("==================================================")
    cohort_def = df_eval[
        (df_eval['position'] == 'DEF') & 
        (df_eval['value'] >= 45) & (df_eval['value'] <= 70) &
        (df_eval['pred_xP'] >= 4.5) & (df_eval['pred_xP'] <= 6.0)
    ]
    cohort_att = df_eval[
        ((df_eval['position'] == 'MID') | (df_eval['position'] == 'FWD')) & 
        (df_eval['value'] >= 100) &
        (df_eval['pred_xP'] >= 4.0) & (df_eval['pred_xP'] <= 5.5)
    ]

    print(f"Cohort A (Defenders £4.5-7.0m, xP 4.5-6.0): {len(cohort_def)} obs")
    print(f"  - Mean Predicted xP : {cohort_def['pred_xP'].mean():.2f}")
    print(f"  - Mean Actual Points: {cohort_def['actual_points'].mean():.2f}")
    print(f"  - Bias (Actual-Pred): {cohort_def['actual_points'].mean() - cohort_def['pred_xP'].mean():.2f}")
    print()
    print(f"Cohort B (Premium Attackers £10.0m+, xP 4.0-5.5): {len(cohort_att)} obs")
    print(f"  - Mean Predicted xP : {cohort_att['pred_xP'].mean():.2f}")
    print(f"  - Mean Actual Points: {cohort_att['actual_points'].mean():.2f}")
    print(f"  - Bias (Actual-Pred): {cohort_att['actual_points'].mean() - cohort_att['pred_xP'].mean():.2f}")
    print()

    # ----------------------------------------------------
    # SECTION 6: PREMIUM ATTACKER HISTORICAL AUDIT
    # ----------------------------------------------------
    print("==================================================")
    print("SECTION 6: PREMIUM ATTACKER HISTORICAL AUDIT")
    print("==================================================")
    premium_mask = (df_eval['value'] >= 100) & ((df_eval['position'] == 'MID') | (df_eval['position'] == 'FWD'))
    premium_df = df_eval[premium_mask]

    p_xg_mean = premium_df['pred_xG'].mean()
    a_g_mean = premium_df['actual_goals'].mean()
    p_xa_mean = premium_df['pred_xA'].mean()
    a_a_mean = premium_df['actual_assists'].mean()
    p_xp_mean = premium_df['pred_xP'].mean()
    a_pts_mean = premium_df['actual_points'].mean()

    print(f"Premium Attackers (£10m+) Evaluation ({len(premium_df)} observations):")
    print(f"  - Mean Predicted xG : {p_xg_mean:.3f} | Mean Actual Goals  : {a_g_mean:.3f} | Bias: {a_g_mean - p_xg_mean:+.3f}")
    print(f"  - Mean Predicted xA : {p_xa_mean:.3f} | Mean Actual Assists: {a_a_mean:.3f} | Bias: {a_a_mean - p_xa_mean:+.3f}")
    print(f"  - Mean Predicted xP : {p_xp_mean:.2f}  | Mean Actual Points: {a_pts_mean:.2f}  | Bias: {a_pts_mean - p_xp_mean:+.2f}")
    print()

    # ----------------------------------------------------
    # SECTION 8 & 9: CLEAN SHEET & DEFCON CALIBRATION
    # ----------------------------------------------------
    print("==================================================")
    print("SECTION 8 & 9: CLEAN SHEET & DEFCON CALIBRATION")
    print("==================================================")
    cs_def_sub = df_eval[df_eval['position'].isin(['DEF', 'GKP'])]
    brier_cs = brier_score_loss((cs_def_sub['actual_cs'] > 0).astype(int), cs_def_sub['pred_CS_prob'])
    print(f"Defender/GKP Clean Sheet Probability Brier Score: {brier_cs:.4f}")
    print(f"Mean Predicted CS Prob: {cs_def_sub['pred_CS_prob'].mean()*100:.1f}% | Mean Actual CS Rate: {(cs_def_sub['actual_cs'] > 0).mean()*100:.1f}%")
    print(f"Clean Sheet Bias: {(cs_def_sub['actual_cs'] > 0).mean() - cs_def_sub['pred_CS_prob'].mean():+.4f}")
    print()

    # ----------------------------------------------------
    # SECTION 11: PRICE TIER VALUE ANALYSIS
    # ----------------------------------------------------
    print("==================================================")
    print("SECTION 11: PRICE TIER VALUE ANALYSIS (xP / £m vs Actual / £m)")
    print("==================================================")
    price_bins = [4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 20.0]
    price_labels = ["£4.0-5.0", "£5.0-6.0", "£6.0-8.0", "£8.0-10.0", "£10.0-12.0", "£12.0+"]
    df_eval['price_tier'] = pd.cut(df_eval['value'] / 10.0, bins=price_bins, labels=price_labels, right=False)

    price_table = []
    for pt in price_labels:
        sub = df_eval[df_eval['price_tier'] == pt]
        if len(sub) == 0:
            continue
        p_val = (sub['pred_xP'] / (sub['value'] / 10.0)).mean()
        a_val = (sub['actual_points'] / (sub['value'] / 10.0)).mean()
        price_table.append({
            "tier": pt,
            "count": len(sub),
            "pred_xp_per_m": round(p_val, 2),
            "act_pts_per_m": round(a_val, 2),
            "val_bias": round(a_val - p_val, 2)
        })
    print(f"{'Price Tier':<12} | {'Count':<7} | {'Pred xP/£m':<12} | {'Act Pts/£m':<12} | {'Value Bias':<10}")
    print("-" * 60)
    for r in price_table:
        print(f"{r['tier']:<12} | {r['count']:<7} | {r['pred_xp_per_m']:<12.2f} | {r['act_pts_per_m']:<12.2f} | {r['val_bias']:<10.2f}")
    print()

    # ----------------------------------------------------
    # SECTION 13: CURRENT 2026/27 SNAPSHOT DIAGNOSTIC TABLE
    # ----------------------------------------------------
    print("==================================================")
    print("SECTION 13: CURRENT 2026/27 SNAPSHOT DIAGNOSTIC TABLE")
    print("==================================================")
    db = SessionLocal()
    try:
        engine = ProjectionEngine(db=db)
        snap_names = ["O'Reilly", "Calafiori", "Gabriel", "Raya", "Gvardiol", "Saka", "Haaland", "B.Fernandes", "Palmer", "João Pedro"]
        snap_rows = []
        for name in snap_names:
            p = db.query(Player).filter(Player.web_name.ilike(f"%{name}%")).first()
            if not p:
                continue
            fix = db.query(Fixture).filter(
                ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                Fixture.event_id == 1
            ).first()
            is_h = (fix.team_h_id == p.team_id)
            opp_i = fix.team_a_id if is_h else fix.team_h_id
            opp_t = db.query(Team).filter(Team.id == opp_i).first()
            bd = engine.calculate_player_xp_breakdown(p, fixture=fix, is_home=is_h, opp_team=opp_t)

            val_m = bd['total_xp'] / max(4.0, p.now_cost / 10.0)
            snap_rows.append({
                "player": p.web_name,
                "position": p.element_type,
                "price": f"£{p.now_cost/10.0:.1f}m",
                "fixture": bd['opponent'],
                "xMins": f"{bd['xMins']:.1f}m",
                "xG": bd['xg_match'],
                "xA": bd['xa_match'],
                "cs_prob": f"{bd['cs_prob']*100:.1f}%",
                "defcon_prob": f"{bd['defcon_prob']*100:.1f}%",
                "pred_xP": bd['total_xp'],
                "xP_per_m": round(val_m, 2)
            })

        print(f"{'Player':<15} | {'Pos':<4} | {'Price':<6} | {'Fixture':<10} | {'xMins':<6} | {'xG':<6} | {'xA':<6} | {'CS Prob':<8} | {'DEFCON':<7} | {'xP':<5} | {'xP/£m':<6}")
        print("-" * 95)
        for r in snap_rows:
            print(f"{r['player']:<15} | {r['position']:<4} | {r['price']:<6} | {r['fixture']:<10} | {r['xMins']:<6} | {r['xG']:<6.3f} | {r['xA']:<6.3f} | {r['cs_prob']:<8} | {r['defcon_prob']:<7} | {r['pred_xP']:<5.2f} | {r['xP_per_m']:<6.2f}")
        print()

    finally:
        db.close()

if __name__ == "__main__":
    run_phase3g_audit()
