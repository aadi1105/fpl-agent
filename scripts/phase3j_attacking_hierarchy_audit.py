import os
import sys
import json
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error

sys.path.append(os.getcwd())

from backend.database import SessionLocal
from backend.models import Player, Fixture, Team
from backend.projections.engine import ProjectionEngine
from scripts.phase3h_calibration_engine import load_and_prep_datasets

def run_phase3j_audit():
    print("=" * 80)
    print("PHASE 3J — ATTACKING ROLE, PRICE-TIER & FPL SCORING HIERARCHY AUDIT")
    print("=" * 80)

    # Step 1: Load Leak-Free Chronological Evaluation Dataset
    df_eval = load_and_prep_datasets()
    df_att = df_eval[df_eval['position'].isin(['MID', 'FWD'])].copy().reset_index(drop=True)

    print(f"Loaded {len(df_att)} active historical attacking observations across 4 seasons.\n")

    # Define Role Proxies
    def assign_role(row):
        pos = row['position']
        xg90 = row.get('xg_per_90_last_5', 0.0)
        xa90 = row.get('xa_per_90_last_5', 0.0)
        if pos == 'FWD':
            if xg90 >= 0.40: return "Elite Striker"
            else: return "Standard Striker"
        else:
            if xg90 >= 0.25 and xa90 < 0.20: return "Inside Forward / Goalscoring Winger"
            elif xa90 >= 0.20: return "Creative Winger / Playmaker"
            else: return "Central / Box-to-Box Midfielder"

    df_att['role_proxy'] = df_att.apply(assign_role, axis=1)

    # ----------------------------------------------------
    # SECTION 2: HISTORICAL FPL SCORING BY ATTACKING ROLE
    # ----------------------------------------------------
    print("=" * 80)
    print("SECTION 2: HISTORICAL FPL SCORING BY ATTACKING ROLE")
    print("=" * 80)
    print(f"{'Role Archetype':<32} | {'Obs':<6} | {'Pts/Game':<8} | {'Pts/90':<8} | {'xG/90':<7} | {'xA/90':<7} | {'Goals/90':<8} | {'Assists/90':<10} | {'Bonus/90':<8}")
    print("-" * 105)
    for role, group in df_att.groupby('role_proxy'):
        mins = group['minutes'].values
        pts = group['total_points'].values
        goals = group['goals_scored'].values
        assists = group['assists'].values
        bonus = group['bonus'].values if 'bonus' in group.columns else np.zeros(len(group))
        
        valid = mins > 0
        pts90 = (pts[valid] / mins[valid]) * 90.0
        g90 = (goals[valid] / mins[valid]) * 90.0
        a90 = (assists[valid] / mins[valid]) * 90.0
        b90 = (bonus[valid] / mins[valid]) * 90.0

        print(f"{role:<32} | {len(group):<6} | {pts.mean():<8.2f} | {pts90.mean():<8.2f} | {group['xg_per_90_last_5'].mean():<7.3f} | {group['xa_per_90_last_5'].mean():<7.3f} | {g90.mean():<8.3f} | {a90.mean():<10.3f} | {b90.mean():<8.3f}")
    print()

    # ----------------------------------------------------
    # SECTION 3: PRICE-TIER ATTACKING ANALYSIS
    # ----------------------------------------------------
    print("=" * 80)
    print("SECTION 3: PRICE-TIER ATTACKING ANALYSIS")
    print("=" * 80)
    # Apply Phase 3H calibration formula
    prem_xg_ratio = 1.882
    non_prem_xg_ratio = 0.984
    prem_xa_ratio = 3.020
    non_prem_xa_ratio = 1.446

    is_prem = (df_att['value'] >= 100)
    df_att['cal_xG'] = np.where(is_prem, df_att['raw_xG'] * prem_xg_ratio, df_att['raw_xG'] * non_prem_xg_ratio)
    df_att['cal_xA'] = np.where(is_prem, df_att['raw_xA'] * prem_xa_ratio, df_att['raw_xA'] * non_prem_xa_ratio)
    
    xMins = df_att['pred_xMins'].values
    pos = df_att['position'].values
    g_mult = np.where(pos == 'MID', 5.0, 4.0)
    c_mult = np.where(pos == 'MID', 1.0, 0.0)
    cs_cal_prob = np.where(df_att['was_home'] == True, 0.142, 0.112)

    goals_xp = df_att['cal_xG'].values * g_mult * (xMins / 90.0)
    assists_xp = df_att['cal_xA'].values * 3.0 * (xMins / 90.0)
    cs_xp = cs_cal_prob * c_mult * (xMins / 90.0)
    app_xp = np.where(xMins >= 60.0, 2.0 * df_att['p_start'].values, np.where(xMins > 0.0, 1.0 * df_att['p_start'].values, 0.0))
    bonus_xp = (goals_xp * 0.4) + (assists_xp * 0.3)
    cards_xp = np.where(xMins > 0.0, -0.09, 0.0)

    df_att['calibrated_xP'] = np.round(app_xp + goals_xp + assists_xp + cs_xp + bonus_xp + cards_xp, 2)
    df_att['actual_points'] = df_att['total_points']

    print(f"{'Price Tier':<12} | {'Obs':<6} | {'Mean Raw xP':<11} | {'Mean Cal xP':<11} | {'Mean Actual Pts':<15} | {'Bias (Act-Cal)':<14} | {'MAE':<6}")
    print("-" * 88)
    tiers = [
        ("£4.5–£6.0m", 45, 60),
        ("£6.0–£8.0m", 60, 80),
        ("£8.0–£10.0m", 80, 100),
        ("£10.0–£12.0m", 100, 120),
        ("£12.0m+", 120, 250)
    ]
    for t_name, p_min, p_max in tiers:
        sub = df_att[(df_att['value'] >= p_min) & (df_att['value'] < p_max)]
        if len(sub) > 0:
            raw_m = sub['raw_xP'].mean()
            cal_m = sub['calibrated_xP'].mean()
            act_m = sub['actual_points'].mean()
            bias = act_m - cal_m
            mae = mean_absolute_error(sub['actual_points'], sub['calibrated_xP'])
            print(f"{t_name:<12} | {len(sub):<6} | {raw_m:<11.2f} | {cal_m:<11.2f} | {act_m:<15.2f} | {bias:<+14.2f} | {mae:<6.2f}")
    print()

    # ----------------------------------------------------
    # SECTION 4 & 5: JOÃO PEDRO & CALVERT-LEWIN FORENSIC COHORT ANALYSIS
    # ----------------------------------------------------
    print("=" * 80)
    print("SECTION 4 & 5: JOÃO PEDRO & CALVERT-LEWIN HISTORICAL COHORT AUDIT")
    print("=" * 80)
    
    # Cohort for João Pedro (£7.0-8.0m FWD/MID with ~0.20-0.25 xG/90)
    jp_cohort = df_att[(df_att['value'] >= 70) & (df_att['value'] <= 80) & (df_att['xg_per_90_last_5'] >= 0.18) & (df_att['xg_per_90_last_5'] <= 0.28)]
    print(f"Historical Cohort for João Pedro (£7.0-8.0m, xG/90 0.18-0.28): {len(jp_cohort)} observations")
    print(f"  - Cohort Mean Predicted Raw xP  : {jp_cohort['raw_xP'].mean():.2f} pts")
    print(f"  - Cohort Mean Calibrated xP     : {jp_cohort['calibrated_xP'].mean():.2f} pts")
    print(f"  - Cohort Mean Actual FPL Points : {jp_cohort['actual_points'].mean():.2f} pts")
    print(f"  - Cohort Bias (Actual - Cal)    : {jp_cohort['actual_points'].mean() - jp_cohort['calibrated_xP'].mean():+.2f} pts")
    print()

    # Cohort for Calvert-Lewin (£6.0m FWD with ~0.20-0.25 xG/90)
    dcl_cohort = df_att[(df_att['value'] >= 55) & (df_att['value'] <= 65) & (df_att['position'] == 'FWD') & (df_att['xg_per_90_last_5'] >= 0.18) & (df_att['xg_per_90_last_5'] <= 0.28)]
    print(f"Historical Cohort for Calvert-Lewin (£5.5-6.5m FWD, xG/90 0.18-0.28): {len(dcl_cohort)} observations")
    print(f"  - Cohort Mean Predicted Raw xP  : {dcl_cohort['raw_xP'].mean():.2f} pts")
    print(f"  - Cohort Mean Calibrated xP     : {dcl_cohort['calibrated_xP'].mean():.2f} pts")
    print(f"  - Cohort Mean Actual FPL Points : {dcl_cohort['actual_points'].mean():.2f} pts")
    print(f"  - Cohort Bias (Actual - Cal)    : {dcl_cohort['actual_points'].mean() - dcl_cohort['calibrated_xP'].mean():+.2f} pts")
    print()

    # ----------------------------------------------------
    # SECTION 9: HISTORICAL FPL POINTS AS A PREDICTIVE SIGNAL EXPERIMENT
    # ----------------------------------------------------
    print("=" * 80)
    print("SECTION 9: HISTORICAL FPL POINTS SIGNAL OUT-OF-SAMPLE EXPERIMENT")
    print("=" * 80)
    
    test_df = df_att[df_att['season'] == '2025-26'].copy().reset_index(drop=True)
    
    # Feature: Recent FPL points/90 (last 5 GWs)
    pts_last_5 = test_df['total_points'].values # proxy
    cal_xp = test_df['calibrated_xP'].values
    act_pts = test_df['actual_points'].values

    # Model A: Current Calibrated xP
    mae_a = mean_absolute_error(act_pts, cal_xp)
    rmse_a = np.sqrt(mean_squared_error(act_pts, cal_xp))
    sp_a, _ = spearmanr(cal_xp, act_pts)

    # Model C: Calibrated xP + Rolling FPL Points/90 Blend (0.85 xP + 0.15 recent FPL pts/90)
    recent_fpl_signal = (test_df['mins_last_5'] / 90.0) * (test_df['xg_last_5'] * 4.0 + test_df['xa_last_5'] * 3.0)
    model_c_xp = 0.85 * cal_xp + 0.15 * np.clip(recent_fpl_signal, 0.0, 10.0)
    mae_c = mean_absolute_error(act_pts, model_c_xp)
    rmse_c = np.sqrt(mean_squared_error(act_pts, model_c_xp))
    sp_c, _ = spearmanr(model_c_xp, act_pts)

    print(f"{'Model Architecture':<40} | {'MAE':<8} | {'RMSE':<8} | {'Spearman':<10}")
    print("-" * 72)
    print(f"{'Model A: Current Calibrated xP':<40} | {mae_a:<8.4f} | {rmse_a:<8.4f} | {sp_a:<10.4f}")
    print(f"{'Model C: Calibrated xP + FPL Signal Blend':<40} | {mae_c:<8.4f} | {rmse_c:<8.4f} | {sp_c:<10.4f}")
    print()

    # ----------------------------------------------------
    # SECTION 12: CURRENT 2026/27 FULL ATTACKER GW1 RANKING
    # ----------------------------------------------------
    print("=" * 80)
    print("SECTION 12: CURRENT 2026/27 GW1 FULL ATTACKER RANKING (MID & FWD)")
    print("=" * 80)
    db = SessionLocal()
    try:
        engine = ProjectionEngine(db=db)
        att_players = db.query(Player).filter(Player.element_type.in_(['MID', 'FWD'])).all()
        
        att_rows = []
        for p in att_players:
            fix = db.query(Fixture).filter(
                ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                Fixture.event_id == 1
            ).first()
            if not fix: continue
            is_h = (fix.team_h_id == p.team_id)
            opp_i = fix.team_a_id if is_h else fix.team_h_id
            opp_t = db.query(Team).filter(Team.id == opp_i).first()
            p_team = db.query(Team).filter(Team.id == p.team_id).first()
            bd = engine.calculate_player_xp_breakdown(p, fixture=fix, is_home=is_h, opp_team=opp_t)

            att_rows.append({
                "name": p.web_name,
                "position": p.element_type,
                "club": p_team.short_name if p_team else "UNK",
                "price": p.now_cost / 10.0,
                "fixture": bd["opponent"],
                "xMins": bd["xMins"],
                "raw_xG": bd["xg_match"],
                "raw_xA": bd["xa_match"],
                "raw_xP": bd["raw_xp"],
                "calibrated_xP": bd["calibrated_xp"]
            })

        df_att_curr = pd.DataFrame(att_rows).sort_values(by="calibrated_xP", ascending=False).reset_index(drop=True)
        print(f"Total Active Attacking Players (MID & FWD): {len(df_att_curr)}")
        print(f"{'Rank':<4} | {'Player':<15} | {'Pos':<4} | {'Club':<5} | {'Price':<6} | {'GW1 Fixture':<10} | {'xMins':<6} | {'Raw xG':<7} | {'Raw xA':<7} | {'Raw xP':<7} | {'Cal xP':<7}")
        print("-" * 95)
        
        highlight_names = ["Haaland", "B.Fernandes", "Saka", "Palmer", "João Pedro", "Calvert-Lewin", "Marmoush", "Osula", "Awoniyi", "Cherki", "Foden", "Dango", "Savinho", "Semenyo"]
        
        for i, r in df_att_curr.iterrows():
            is_hl = any(h.lower() in r['name'].lower() for h in highlight_names)
            if i < 25 or is_hl:
                mark = "  <-- HIGHLIGHTED" if is_hl else ""
                print(f"{i+1:<4} | {r['name']:<15} | {r['position']:<4} | {r['club']:<5} | £{r['price']:<5.1f}m | {r['fixture']:<10} | {r['xMins']:<6.1f} | {r['raw_xG']:<7.3f} | {r['raw_xA']:<7.3f} | {r['raw_xP']:<7.2f} | {r['calibrated_xP']:<7.2f}{mark}")
        print()

    finally:
        db.close()

if __name__ == "__main__":
    run_phase3j_audit()
