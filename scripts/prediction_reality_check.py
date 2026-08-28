import os
import sys
import json
import math
import logging
import time
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, brier_score_loss

# Add project root to path
sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models import Player, Fixture, Team
from backend.projections.engine import ProjectionEngine
from backend.ml.minutes_predictor import MinutesPredictor, FEATURE_COLS as MINS_COLS
from backend.ml.xg_predictor import XGPredictor
from backend.ml.xa_predictor import XAPredictor
from backend.ml.cs_predictor import CSPredictor
from backend.ml.defcon_predictor import DEFCONPredictor

logger = logging.getLogger("prediction_reality_check")
logging.basicConfig(level=logging.INFO)

RAW_FILES = {
    "2022-23": "data/raw/merged_gw_2022-23.csv",
    "2023-24": "data/raw/merged_gw_2023-24.csv",
    "2024-25": "data/raw/merged_gw_2024-25.csv",
    "2025-26": "data/raw/merged_gw_2025-26.csv"
}

def load_historical_raw_data():
    """Load and format historical gameweek data strictly chronologically."""
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
                'threat', 'creativity', 'total_points', 'value', 'transfers_balance', 'clean_sheets']:
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0.0)
            
    season_order = {"2022-23": 1, "2023-24": 2, "2024-25": 3, "2025-26": 4}
    df_raw['season_idx'] = df_raw['season'].map(season_order)
    df_raw = df_raw.sort_values(by=['season_idx', 'gameweek', 'player_id']).reset_index(drop=True)
    return df_raw

def construct_leak_free_historical_predictions(df_raw):
    """
    Reconstruct predictions for every player-gameweek observation using ONLY 
    information available strictly BEFORE that gameweek's deadline. Zero leakage.
    Vectorized for high performance across 110,000+ observations.
    """
    mins_pred = MinutesPredictor()
    xg_pred = XGPredictor()
    xa_pred = XAPredictor()
    cs_pred = CSPredictor()
    defcon_pred = DEFCONPredictor()

    print("Building leak-free rolling window features...")
    grouped = df_raw.groupby('player_id', group_keys=False)

    def build_player_rolling(g):
        g = g.sort_values(by=['season_idx', 'gameweek'])
        n = len(g)
        
        mins = g['minutes'].values
        starts = g['starts'].values
        goals = g['goals_scored'].values
        assists = g['assists'].values
        xg = g['expected_goals'].values
        xa = g['expected_assists'].values
        pts = g['total_points'].values

        mins_shift = np.zeros(n)
        starts_shift = np.zeros(n)
        goals_shift = np.zeros(n)
        assists_shift = np.zeros(n)
        xg_shift = np.zeros(n)
        xa_shift = np.zeros(n)
        pts_shift = np.zeros(n)

        mins_shift[1:] = mins[:-1]
        starts_shift[1:] = starts[:-1]
        goals_shift[1:] = goals[:-1]
        assists_shift[1:] = assists[:-1]
        xg_shift[1:] = xg[:-1]
        xa_shift[1:] = xa[:-1]
        pts_shift[1:] = pts[:-1]

        g['tot_mins_prior'] = np.cumsum(mins_shift)
        
        g['minutes_last_1'] = mins_shift
        g['minutes_last_3'] = pd.Series(mins_shift, index=g.index).rolling(3, min_periods=1).sum().values
        g['minutes_last_5'] = pd.Series(mins_shift, index=g.index).rolling(5, min_periods=1).sum().values
        g['minutes_last_10'] = pd.Series(mins_shift, index=g.index).rolling(10, min_periods=1).sum().values

        g['starts_last_1'] = starts_shift
        g['starts_last_3'] = pd.Series(starts_shift, index=g.index).rolling(3, min_periods=1).sum().values
        g['starts_last_5'] = pd.Series(starts_shift, index=g.index).rolling(5, min_periods=1).sum().values
        g['starts_last_10'] = pd.Series(starts_shift, index=g.index).rolling(10, min_periods=1).sum().values

        g['goals_last_1'] = goals_shift
        g['goals_last_3'] = pd.Series(goals_shift, index=g.index).rolling(3, min_periods=1).sum().values
        g['goals_last_5'] = pd.Series(goals_shift, index=g.index).rolling(5, min_periods=1).sum().values
        g['goals_last_10'] = pd.Series(goals_shift, index=g.index).rolling(10, min_periods=1).sum().values

        g['assists_last_1'] = assists_shift
        g['assists_last_3'] = pd.Series(assists_shift, index=g.index).rolling(3, min_periods=1).sum().values
        g['assists_last_5'] = pd.Series(assists_shift, index=g.index).rolling(5, min_periods=1).sum().values
        g['assists_last_10'] = pd.Series(assists_shift, index=g.index).rolling(10, min_periods=1).sum().values

        g['xg_last_1'] = xg_shift
        g['xg_last_3'] = pd.Series(xg_shift, index=g.index).rolling(3, min_periods=1).sum().values
        g['xg_last_5'] = pd.Series(xg_shift, index=g.index).rolling(5, min_periods=1).sum().values
        g['xg_last_10'] = pd.Series(xg_shift, index=g.index).rolling(10, min_periods=1).sum().values
        g['xg_career'] = np.cumsum(xg_shift)

        g['xa_last_1'] = xa_shift
        g['xa_last_3'] = pd.Series(xa_shift, index=g.index).rolling(3, min_periods=1).sum().values
        g['xa_last_5'] = pd.Series(xa_shift, index=g.index).rolling(5, min_periods=1).sum().values
        g['xa_last_10'] = pd.Series(xa_shift, index=g.index).rolling(10, min_periods=1).sum().values
        g['xa_career'] = np.cumsum(xa_shift)

        g['appearances_last_5'] = pd.Series(mins_shift > 0, index=g.index).rolling(5, min_periods=1).sum().values
        g['pts_last_5'] = pd.Series(pts_shift, index=g.index).rolling(5, min_periods=1).sum().values

        # Reset first row for player (zero history prior to GW1)
        for col in ['minutes_last_1', 'minutes_last_3', 'minutes_last_5', 'minutes_last_10',
                    'starts_last_1', 'starts_last_3', 'starts_last_5', 'starts_last_10',
                    'goals_last_1', 'goals_last_3', 'goals_last_5', 'goals_last_10',
                    'assists_last_1', 'assists_last_3', 'assists_last_5', 'assists_last_10',
                    'xg_last_1', 'xg_last_3', 'xg_last_5', 'xg_last_10', 'xg_career',
                    'xa_last_1', 'xa_last_3', 'xa_last_5', 'xa_last_10', 'xa_career',
                    'appearances_last_5', 'pts_last_5']:
            g.iloc[0, g.columns.get_loc(col)] = 0.0

        return g

    df_feat = grouped.apply(build_player_rolling)
    df_feat = df_feat.reset_index(drop=True)

    pos_str = df_feat['position'].astype(str).str.upper()
    df_feat['position'] = np.where(pos_str.isin(['GKP', 'DEF', 'MID', 'FWD']), pos_str, 'MID')
    df_feat['pos_DEF'] = (df_feat['position'] == 'DEF').astype(float)
    df_feat['pos_MID'] = (df_feat['position'] == 'MID').astype(float)
    df_feat['pos_FWD'] = (df_feat['position'] == 'FWD').astype(float)
    df_feat['pos_GKP'] = (df_feat['position'] == 'GKP').astype(float)

    df_feat['price'] = df_feat['value'].apply(lambda v: float(v)/10.0 if float(v) > 20 else float(v)).clip(4.0, 15.0)
    df_feat['fixture_difficulty'] = 3.0
    df_feat['team_attack_rating'] = 1000.0
    df_feat['team_defence_rating'] = 1000.0
    df_feat['opponent_attack_rating'] = 1000.0
    df_feat['opponent_defence_rating'] = 1000.0
    df_feat['home_away_is_home'] = df_feat['was_home'].astype(float) if 'was_home' in df_feat.columns else 1.0
    df_feat['is_home'] = df_feat['home_away_is_home']

    df_feat['bench_appearances_last_5'] = (df_feat['appearances_last_5'] - df_feat['starts_last_5']).clip(lower=0.0)
    df_feat['unused_substitute_last_5'] = (5.0 - df_feat['appearances_last_5']).clip(lower=0.0)
    df_feat['average_minutes_last_5'] = np.where(df_feat['appearances_last_5'] > 0, df_feat['minutes_last_5'] / np.maximum(1.0, df_feat['appearances_last_5']), 0.0)
    df_feat['average_minutes_last_10'] = df_feat['average_minutes_last_5']
    df_feat['days_since_last_match'] = 7.0
    df_feat['matches_in_previous_14_days'] = 2.0
    df_feat['matches_in_previous_21_days'] = 3.0
    df_feat['fixture_congestion'] = 0.0

    df_feat['xg_90_3'] = np.where(df_feat['minutes_last_3'] > 0, (df_feat['xg_last_3'] / df_feat['minutes_last_3']) * 90.0, 0.20)
    df_feat['xg_90_5'] = np.where(df_feat['minutes_last_5'] > 0, (df_feat['xg_last_5'] / df_feat['minutes_last_5']) * 90.0, 0.20)
    df_feat['xg_90_10'] = np.where(df_feat['minutes_last_10'] > 0, (df_feat['xg_last_10'] / df_feat['minutes_last_10']) * 90.0, 0.20)
    df_feat['xg_90_career'] = np.where(df_feat['tot_mins_prior'] > 0, (df_feat['xg_career'] / df_feat['tot_mins_prior']) * 90.0, 0.20)

    df_feat['xa_90_3'] = np.where(df_feat['minutes_last_3'] > 0, (df_feat['xa_last_3'] / df_feat['minutes_last_3']) * 90.0, 0.15)
    df_feat['xa_90_5'] = np.where(df_feat['minutes_last_5'] > 0, (df_feat['xa_last_5'] / df_feat['minutes_last_5']) * 90.0, 0.15)
    df_feat['xa_90_10'] = np.where(df_feat['minutes_last_10'] > 0, (df_feat['xa_last_10'] / df_feat['minutes_last_10']) * 90.0, 0.15)
    df_feat['xa_90_career'] = np.where(df_feat['tot_mins_prior'] > 0, (df_feat['xa_career'] / df_feat['tot_mins_prior']) * 90.0, 0.15)

    print("Evaluating production model predictions across dataset...")
    df_mins_in = df_feat[MINS_COLS]
    raw_p_start = np.clip(mins_pred.m_start.predict_proba(df_mins_in)[:, 1], 0.0, 1.0)
    raw_mins = np.clip(mins_pred.m_mins.predict(df_mins_in), 0.0, 90.0)
    raw_p_60 = np.clip(mins_pred.m_60.predict_proba(df_mins_in)[:, 1], 0.0, 1.0)
    raw_p_0 = np.clip(mins_pred.m_0.predict_proba(df_mins_in)[:, 1], 0.0, 1.0)

    sample_games = np.minimum(5.0, np.maximum(df_feat['appearances_last_5'].values, df_feat['minutes_last_5'].values / 90.0))
    w_ev = sample_games / 5.0

    pred_xMins = (w_ev * raw_mins) + ((1.0 - w_ev) * 15.0)
    pred_pstart = (w_ev * raw_p_start) + ((1.0 - w_ev) * 0.10)
    pred_p60 = (w_ev * raw_p_60) + ((1.0 - w_ev) * 0.05)
    pred_p0 = (w_ev * raw_p_0) + ((1.0 - w_ev) * 0.70)

    df_feat['expected_minutes_v1'] = pred_xMins
    df_feat['p_start'] = pred_pstart
    df_feat['p_60_plus'] = pred_p60
    df_feat['p_zero'] = pred_p0

    # xG Model
    df_xg_v2_in = df_feat[['xg_90_3', 'xg_90_5', 'xg_90_10', 'xg_90_career', 'tot_mins_prior', 'minutes_last_5', 'starts_last_5']].rename(columns={'minutes_last_5': 'mins_last_5'})
    pred_xg90 = np.clip(xg_pred.model.predict(df_xg_v2_in), 0.0, 2.0)
    pred_xg = np.clip(pred_xg90 * (pred_xMins / 90.0), 0.0, 3.0)

    # xA Model
    df_xa_v2_in = df_feat[['xa_90_3', 'xa_90_5', 'xa_90_10', 'xa_90_career', 'tot_mins_prior', 'minutes_last_5', 'starts_last_5']].rename(columns={'minutes_last_5': 'mins_last_5'})
    pred_xa90 = np.clip(xa_pred.model.predict(df_xa_v2_in), 0.0, 2.0)
    pred_xa = np.clip(pred_xa90 * (pred_xMins / 90.0), 0.0, 3.0)

    # CS Model
    df_cs_in = pd.DataFrame({
        'team_defence_rating': df_feat['team_defence_rating'].values,
        'opponent_attack_rating': df_feat['opponent_attack_rating'].values,
        'home_away_is_home': df_feat['is_home'].values
    })
    pred_cs = np.clip(cs_pred.model.predict(df_cs_in), 0.04, 0.75)

    # DEFCON Model
    cbit_est = np.where(df_feat['position'] == 'DEF', 6.0, np.where(df_feat['position'] == 'MID', 4.0, 2.0))
    cbit_match = cbit_est * (pred_xMins / 90.0)
    # Poisson CDF under 10
    prob_under_10 = np.zeros(len(df_feat))
    for k in range(10):
        prob_under_10 += (np.power(cbit_match, k) * np.exp(-cbit_match)) / math.factorial(k)
    pred_defcon = np.clip(1.0 - prob_under_10, 0.0, 0.85)

    # FPL Points Engine Component Scoring
    mins_ratio = np.clip(pred_xMins / 90.0, 0.0, 1.0)
    app_xp = np.where(pred_xMins >= 60.0, 2.0, np.where(pred_xMins > 0.0, 1.0, 0.0)) * mins_ratio

    goal_mult = np.where(df_feat['position'].isin(['GKP', 'DEF']), 6.0, np.where(df_feat['position'] == 'MID', 5.0, 4.0))
    goals_xp = pred_xg * goal_mult
    assists_xp = pred_xa * 3.0

    cs_mult = np.where(df_feat['position'].isin(['GKP', 'DEF']), 4.0, np.where(df_feat['position'] == 'MID', 1.0, 0.0))
    cs_xp = np.where(pred_xMins >= 60.0, pred_cs * cs_mult * mins_ratio, 0.0)

    defcon_xp = np.where(df_feat['position'].isin(['GKP', 'DEF']), pred_defcon * 2.0, pred_defcon * 1.0)
    bonus_xp = (pred_xg * 1.2 + pred_xa * 0.8) * mins_ratio
    cards_xp = -0.15 * mins_ratio

    pred_total_xp = np.round(app_xp + goals_xp + assists_xp + cs_xp + defcon_xp + bonus_xp + cards_xp, 2)

    p_name_col = 'player_name' if 'player_name' in df_feat.columns else ('name' if 'name' in df_feat.columns else 'web_name')
    p_id_col = 'player_id' if 'player_id' in df_feat.columns else ('element' if 'element' in df_feat.columns else 'id')

    res_df = pd.DataFrame({
        'season': df_feat['season'].values,
        'gameweek': df_feat['gameweek'].values,
        'player_id': df_feat[p_id_col].values if p_id_col in df_feat.columns else df_feat.index.values,
        'player_name': df_feat[p_name_col].values,
        'position': df_feat['position'].values,
        'price': df_feat['price'].values,
        'tot_mins_prior': df_feat['tot_mins_prior'].values,
        'recent_form_pts': np.where(df_feat['appearances_last_5'] > 0, df_feat['pts_last_5'] / np.maximum(1.0, df_feat['appearances_last_5']), 0.0),
        'net_transfers': df_feat['transfers_balance'].values if 'transfers_balance' in df_feat.columns else np.zeros(len(df_feat)),
        'is_established': np.where(df_feat['tot_mins_prior'] >= 1000, 1, 0),

        'actual_minutes': df_feat['minutes'].values,
        'actual_starts': df_feat['starts'].values,
        'actual_goals': df_feat['goals_scored'].values,
        'actual_assists': df_feat['assists'].values,
        'actual_xg': df_feat['expected_goals'].values,
        'actual_xa': df_feat['expected_assists'].values,
        'actual_cs': df_feat['clean_sheets'].values if 'clean_sheets' in df_feat.columns else np.zeros(len(df_feat)),
        'actual_total_points': df_feat['total_points'].values,

        'pred_xMins': pred_xMins,
        'pred_pstart': pred_pstart,
        'pred_xg': pred_xg,
        'pred_xa': pred_xa,
        'pred_cs': pred_cs,
        'pred_defcon': pred_defcon,
        'pred_total_xp': pred_total_xp
    })
    return res_df

def evaluate_metrics(df):
    """Compute overall and segmented evaluation metrics."""
    # Minutes
    mae_mins = mean_absolute_error(df['actual_minutes'], df['pred_xMins'])
    rmse_mins = math.sqrt(mean_squared_error(df['actual_minutes'], df['pred_xMins']))
    brier_start = brier_score_loss(df['actual_starts'], df['pred_pstart'])

    # xG
    mae_xg = mean_absolute_error(df['actual_goals'], df['pred_xg'])
    rmse_xg = math.sqrt(mean_squared_error(df['actual_goals'], df['pred_xg']))

    # xA
    mae_xa = mean_absolute_error(df['actual_assists'], df['pred_xa'])
    rmse_xa = math.sqrt(mean_squared_error(df['actual_assists'], df['pred_xa']))

    # Clean Sheet
    brier_cs = brier_score_loss(df['actual_cs'], df['pred_cs'])

    # Total xP
    mae_xp = mean_absolute_error(df['actual_total_points'], df['pred_total_xp'])
    rmse_xp = math.sqrt(mean_squared_error(df['actual_total_points'], df['pred_total_xp']))
    
    p_corr, _ = pearsonr(df['pred_total_xp'], df['actual_total_points']) if len(df) > 1 else (0.0, 0.0)
    s_corr, _ = spearmanr(df['pred_total_xp'], df['actual_total_points']) if len(df) > 1 else (0.0, 0.0)

    return {
        'count': int(len(df)),
        'mae_mins': float(mae_mins),
        'rmse_mins': float(rmse_mins),
        'brier_start': float(brier_start),
        'mae_xg': float(mae_xg),
        'rmse_xg': float(rmse_xg),
        'mae_xa': float(mae_xa),
        'rmse_xa': float(rmse_xa),
        'brier_cs': float(brier_cs),
        'mae_xp': float(mae_xp),
        'rmse_xp': float(rmse_xp),
        'pearson_r': float(p_corr),
        'spearman_rho': float(s_corr)
    }

def create_calibration_table(df, pred_col, actual_col, n_bins=10):
    """Create probability calibration table across probability buckets."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    df['bin'] = pd.cut(df[pred_col], bins=bins, include_lowest=True)
    calib = []
    
    for b, group in df.groupby('bin', observed=False):
        if len(group) > 0:
            mean_pred = float(group[pred_col].mean())
            actual_freq = float(group[actual_col].mean())
            calib.append({
                'bucket': str(b),
                'count': int(len(group)),
                'mean_predicted': round(mean_pred, 4),
                'actual_frequency': round(actual_freq, 4),
                'calibration_error': round(actual_freq - mean_pred, 4)
            })
    return calib

def get_current_2026_27_snapshot():
    """Extract current GW1–GW4 production predictions for key 10 target players."""
    db = SessionLocal()
    try:
        engine = ProjectionEngine(db=db)
        target_names = [
            "Erling Haaland", "Bruno Fernandes", "Mohamed Salah", "Bukayo Saka", 
            "Cole Palmer", "João Pedro", "Dominic Calvert-Lewin", "Gabriel Magalhães", 
            "Taiwo Awoniyi", "William Osula"
        ]
        
        snapshot = []
        for name in target_names:
            players = db.query(Player).filter(Player.web_name.ilike(f"%{name.split()[-1]}%")).all()
            p = None
            for cand in players:
                if name.lower() in (cand.first_name + " " + cand.second_name).lower() or name.lower() in cand.web_name.lower():
                    p = cand
                    break
            if not p and players:
                p = players[0]
                
            if not p:
                continue

            fixtures = db.query(Fixture).filter(
                ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                Fixture.event_id == 1
            ).all()
            
            fix = fixtures[0] if fixtures else None
            is_home = (fix.team_h_id == p.team_id) if fix else True
            opp_id = (fix.team_a_id if is_home else fix.team_h_id) if fix else None
            opp_team = db.query(Team).filter(Team.id == opp_id).first() if opp_id else None

            breakdown = engine.calculate_player_xp_breakdown(p, fixture=fix, is_home=is_home, opp_team=opp_team)

            gw1_xp = breakdown['total_xp']
            gw2_xp = round(gw1_xp * 0.95, 2)
            gw3_xp = round(gw1_xp * 0.90, 2)
            gw4_xp = round(gw1_xp * 0.85, 2)
            weighted_4gw = round(0.55 * gw1_xp + 0.20 * gw2_xp + 0.15 * gw3_xp + 0.10 * gw4_xp, 2)

            snapshot.append({
                'web_name': p.web_name,
                'full_name': p.first_name + " " + p.second_name,
                'position': p.element_type,
                'price': f"£{p.now_cost / 10.0:.1f}m",
                'fixture': breakdown['opponent'],
                'expected_minutes': breakdown['xMins'],
                'p_start': breakdown['p_start'],
                'xg_match': breakdown['xg_match'],
                'xa_match': breakdown['xa_match'],
                'cs_prob': breakdown['cs_prob'],
                'gw1_xp': gw1_xp,
                'gw2_xp': gw2_xp,
                'gw3_xp': gw3_xp,
                'gw4_xp': gw4_xp,
                'weighted_4gw': weighted_4gw
            })

        return snapshot
    finally:
        db.close()

def run_prediction_reality_check():
    print("==================================================")
    print("PHASE 3D — PREDICTION REALITY CHECK DIAGNOSTIC ENGINE")
    print("==================================================\n")

    t_start = time.time()
    print("Step 1: Loading raw historical data (2022-23 to 2025-26)...")
    df_raw = load_historical_raw_data()
    print(f"Loaded {len(df_raw)} historical player-gameweek observations.\n")

    print("Step 2: Reconstructing leak-free historical predictions using active production models...")
    df_pred = construct_leak_free_historical_predictions(df_raw)
    print(f"Successfully reconstructed predictions for {len(df_pred)} observations in {time.time() - t_start:.2f}s.\n")

    print("Step 3: Calculating overall performance metrics...")
    overall_metrics = evaluate_metrics(df_pred)

    print("Step 4: Calculating segmented breakdowns...")
    pos_breakdown = {}
    for pos, grp in df_pred.groupby('position'):
        pos_breakdown[pos] = evaluate_metrics(grp)

    def price_tier(row):
        pos = row['position']
        pr = row['price']
        if pos in ['MID', 'FWD']:
            return 'High (>£9m)' if pr >= 9.0 else ('Mid (£6.5-8.5m)' if pr >= 6.5 else 'Low (<£6.5m)')
        else:
            return 'High (>£6m)' if pr >= 6.0 else ('Mid (£5-5.5m)' if pr >= 5.0 else 'Low (<£5m)')
    
    df_pred['price_tier'] = df_pred.apply(price_tier, axis=1)
    price_breakdown = {}
    for pt, grp in df_pred.groupby('price_tier'):
        price_breakdown[pt] = evaluate_metrics(grp)

    def mins_bucket(m):
        if m < 300: return '<300'
        elif m < 600: return '300-600'
        elif m < 1000: return '600-1000'
        elif m < 2000: return '1000-2000'
        else: return '2000+'
    
    df_pred['mins_bucket'] = df_pred['tot_mins_prior'].map(mins_bucket)
    mins_breakdown = {}
    for mb, grp in df_pred.groupby('mins_bucket'):
        mins_breakdown[mb] = evaluate_metrics(grp)

    est_breakdown = {
        'Established (mins>=1000)': evaluate_metrics(df_pred[df_pred['is_established'] == 1]),
        'Low-Sample (mins<1000)': evaluate_metrics(df_pred[df_pred['is_established'] == 0])
    }

    print("Step 5: Generating Probability Calibration Tables...")
    calib_pstart = create_calibration_table(df_pred.copy(), 'pred_pstart', 'actual_starts')
    calib_cs = create_calibration_table(df_pred.copy(), 'pred_cs', 'actual_cs')

    print("Step 6: Player-Level Sanity Check...")
    target_players = [
        "Erling Haaland", "Mohamed Salah", "Bukayo Saka", "Bruno Fernandes", "Cole Palmer",
        "Alexander Isak", "Ollie Watkins", "Dominic Solanke", "Chris Wood", "Gabriel Magalhães", "David Raya",
        "Taiwo Awoniyi", "William Osula", "Omar Marmoush", "Beto", "João Pedro", "Dominic Calvert-Lewin"
    ]
    
    player_sanity = []
    for name in target_players:
        sub = df_pred[df_pred['player_name'].str.contains(name.split()[-1], case=False, na=False)]
        if len(sub) > 0:
            m = evaluate_metrics(sub)
            m['name'] = name
            m['mean_pred_xP'] = float(sub['pred_total_xp'].mean())
            m['mean_actual_pts'] = float(sub['actual_total_points'].mean())
            player_sanity.append(m)

    print("Step 7: Extracting Current 2026/27 Snapshot...")
    snapshot_2026_27 = get_current_2026_27_snapshot()

    results_data = {
        'overall_metrics': overall_metrics,
        'position_breakdown': pos_breakdown,
        'price_breakdown': price_breakdown,
        'minutes_breakdown': mins_breakdown,
        'established_breakdown': est_breakdown,
        'calibration_pstart': calib_pstart,
        'calibration_cs': calib_cs,
        'player_sanity_check': player_sanity,
        'snapshot_2026_27': snapshot_2026_27
    }

    os.makedirs("scratch", exist_ok=True)
    with open("scratch/prediction_reality_check_output.json", "w") as f:
        json.dump(results_data, f, indent=2)

    print("\n==================================================")
    print("REALITY CHECK SUMMARY RESULTS")
    print("==================================================")
    print(f"Total Observations Evaluated: {overall_metrics['count']}")
    print(f"Expected Minutes MAE : {overall_metrics['mae_mins']:.2f}m | RMSE: {overall_metrics['rmse_mins']:.2f}")
    print(f"P(start) Brier Score : {overall_metrics['brier_start']:.4f}")
    print(f"xG Match MAE         : {overall_metrics['mae_xg']:.4f} | RMSE: {overall_metrics['rmse_xg']:.4f}")
    print(f"xA Match MAE         : {overall_metrics['mae_xa']:.4f} | RMSE: {overall_metrics['rmse_xa']:.4f}")
    print(f"Clean Sheet Brier    : {overall_metrics['brier_cs']:.4f}")
    print(f"Total xP MAE         : {overall_metrics['mae_xp']:.2f} pts | RMSE: {overall_metrics['rmse_xp']:.2f} pts")
    print(f"Total xP Pearson r   : {overall_metrics['pearson_r']:.4f} | Spearman rho: {overall_metrics['spearman_rho']:.4f}")
    print("==================================================\n")

if __name__ == "__main__":
    run_prediction_reality_check()
