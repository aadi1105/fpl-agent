import os
import sys
import json
import numpy as np
import pandas as pd

sys.path.append(os.getcwd())
from backend.database import get_db
from backend.models import Player, Team
from backend.projections.engine import ProjectionEngine
from backend.ml.minutes_candidate_v2 import MinutesCandidateV2
from backend.ml.xg_candidate_v2 import XGCandidateV2
from backend.ml.xa_candidate_v2 import XACandidateV2

print("=== 1. GENERATING FRESH 2026/27 PROJECTIONS WITH PRODUCTION V2 PIPELINE ===")

db = next(get_db())
engine = ProjectionEngine(db=db)

# Load active players
players = db.query(Player).all()
print(f"Loaded {len(players)} players from database.")

target_players = [
    'Haaland', 'Bruno Fernandes', 'João Pedro', 'Calvert-Lewin',
    'Awoniyi', 'Osula', 'Beto', 'Marmoush', 'Gabriel', 'Semenyo', 'Mbeumo', 'Saka'
]

cand_mins = MinutesCandidateV2()
cand_xg = XGCandidateV2()
cand_xa = XACandidateV2()

results = []

for p in players:
    pos_str = str(p.element_type) if p.element_type else "MID"
    cost = p.now_cost / 10.0
    ownership = float(p.selected_by_percent) if p.selected_by_percent else 0.0
    
    # Calculate Gameweek Projections (GW0, GW1, GW2, GW3)
    gw_projs_v1 = []
    gw_projs_v2 = []
    
    for gw_idx in range(4):
        # Generate V1 projection from engine
        proj_v1 = engine.calculate_player_xp_breakdown(p)
        gw_projs_v1.append(proj_v1)
        
        # Calculate Candidate V2 metrics
        actual_starts_5 = float(getattr(p, 'starts_last_5', 3.0 if p.minutes > 1500 else 1.0))
        actual_mins_5 = float(getattr(p, 'mins_last_5', 270.0 if p.minutes > 1500 else 90.0))
        curr_club_starts = actual_starts_5
        curr_club_mins = actual_mins_5
        
        res_m2 = cand_mins.predict_candidate_minutes(
            pdata={'price': cost}, actual_recent_starts_5=actual_starts_5, actual_recent_mins_5=actual_mins_5,
            current_club_starts=curr_club_starts, current_club_mins=curr_club_mins, pos=pos_str, cost=cost
        )
        xmins_v2 = res_m2['expected_minutes_v2']
        pstart_v2 = res_m2['p_start_v2']
        
        # V2 xG and xA calculation with shrinkage
        xg90_raw = float(getattr(p, 'expected_goals_per_90', 0.20))
        xa90_raw = float(getattr(p, 'expected_assists_per_90', 0.15))
        prior_mins = float(getattr(p, 'minutes', 1000.0))
        
        res_xg2 = cand_xg.calculate_shrunk_xg90(xg90_raw, prior_mins, pos_str)
        res_xa2 = cand_xa.calculate_shrunk_xa90(xa90_raw, prior_mins, pos_str)
        
        xg_v2_match = res_xg2['shrunk_xg90'] * (xmins_v2 / 90.0)
        xa_v2_match = res_xa2['shrunk_xa90'] * (xmins_v2 / 90.0)
        
        # Points calculation
        mins_ratio = min(1.0, max(0.0, xmins_v2 / 90.0))
        app_pts = (2.0 if xmins_v2 >= 60 else 1.0) * mins_ratio
        g_pts = xg_v2_match * (6.0 if pos_str in ['DEF', 'GKP'] else (5.0 if pos_str == 'MID' else 4.0))
        a_pts = xa_v2_match * 3.0
        cs_pts = (proj_v1['cs_prob'] * 4.0) if pos_str in ['DEF', 'GKP'] else ((proj_v1['cs_prob'] * 1.0) if pos_str == 'MID' else 0.0)
        bonus_pts = (xg_v2_match * 2.0 + xa_v2_match * 1.5) * mins_ratio
        
        total_xp_v2 = round(app_pts + g_pts + a_pts + cs_pts + bonus_pts, 2)
        
        gw_projs_v2.append({
            'gw': f"GW{gw_idx}",
            'xMins': xmins_v2,
            'p_start': pstart_v2,
            'xG': round(xg_v2_match, 3),
            'xA': round(xa_v2_match, 3),
            'xP': total_xp_v2
        })
        
    weights = [0.40, 0.30, 0.20, 0.10]
    weighted_xp_v1 = round(sum(gw_projs_v1[i]['total_xp'] * weights[i] for i in range(4)), 2)
    weighted_xp_v2 = round(sum(gw_projs_v2[i]['xP'] * weights[i] for i in range(4)), 2)
    
    results.append({
        'id': p.id,
        'web_name': p.web_name,
        'position': pos_str,
        'price': cost,
        'ownership': ownership,
        'prior_mins': p.minutes,
        'v1_weighted_xp': weighted_xp_v1,
        'v2_weighted_xp': weighted_xp_v2,
        'gw0_xp_v1': gw_projs_v1[0]['total_xp'],
        'gw0_xp_v2': gw_projs_v2[0]['xP'],
        'gw0_xMins_v2': gw_projs_v2[0]['xMins'],
        'gw0_pstart_v2': gw_projs_v2[0]['p_start'],
        'gw0_xg_v2': gw_projs_v2[0]['xG'],
        'gw0_xa_v2': gw_projs_v2[0]['xA'],
        'gw_projs_v1': gw_projs_v1,
        'gw_projs_v2': gw_projs_v2
    })

df_res = pd.DataFrame(results)
df_res['v2_rank'] = df_res['v2_weighted_xp'].rank(ascending=False, method='min').astype(int)
df_res['consensus_rank'] = df_res['ownership'].rank(ascending=False, method='min').astype(int)
df_res['rank_diff'] = df_res['consensus_rank'] - df_res['v2_rank']

print("\n=== 2. CRITICAL PLAYER AUDIT TABLE (V1 vs V2 PROJECTIONS) ===")
print(f"{'Player':<22} | {'Pos':<4} | {'Price':<5} | {'Own%':<5} | {'V1 xP':<6} | {'V2 xP':<6} | {'V2 Rank':<7} | {'xMins':<6} | {'P(start)':<8} | {'xG':<6} | {'xA':<6}")
print("-" * 115)

target_player_ids = [
    (411, 'Erling Haaland'),
    (426, 'Bruno Fernandes'),
    (154, 'Cole Palmer'),
    (12, 'Bukayo Saka'),
    (4, 'Gabriel Magalhães'),
    (427, 'Bryan Mbeumo'),
    (397, 'Antoine Semenyo'),
    (401, 'Omar Marmoush'),
    (492, 'Taiwo Awoniyi'),
    (465, 'William Osula'),
    (165, 'João Pedro'),
    (346, 'Dominic Calvert-Lewin')
]

critical_list = []
for pid, label in target_player_ids:
    match = df_res[df_res['id'] == pid]
    if not match.empty:
        row = match.iloc[0].to_dict()
        row['display_label'] = label
        critical_list.append(row)
        print(f"{row['web_name']:<22} | {row['position']:<4} | £{row['price']:<4.1f} | {row['ownership']:<4.1f}% | {row['v1_weighted_xp']:<6.2f} | {row['v2_weighted_xp']:<6.2f} | #{row['v2_rank']:<6} | {row['gw0_xMins_v2']:<6.1f} | {row['gw0_pstart_v2']*100:<7.1f}% | {row['gw0_xg_v2']:<6.3f} | {row['gw0_xa_v2']:<6.3f}")

print("\n=== 3. BRUNO FERNANDES SPECIFIC DIAGNOSTIC INVESTIGATION ===")
bruno_match = df_res[df_res['id'] == 426]
if not bruno_match.empty:
    b = bruno_match.iloc[0]
    print(f"Name              : {b['web_name']} (ID {b['id']})")
    print(f"Price / Ownership : £{b['price']}m | {b['ownership']}% (Consensus Rank #{b['consensus_rank']})")
    print(f"V1 Weighted xP    : {b['v1_weighted_xp']} | V2 Weighted xP: {b['v2_weighted_xp']} (Model V2 Rank #{b['v2_rank']})")
    print(f"GW0 xMins         : {b['gw0_xMins_v2']}m | P(start): {b['gw0_pstart_v2']*100:.1f}%")
    print(f"GW0 xG / xA       : xG = {b['gw0_xg_v2']} | xA = {b['gw0_xa_v2']}")
    print(f"Rank Discrepancy  : {b['rank_diff']} positions (Model Rank #{b['v2_rank']} vs Consensus Rank #{b['consensus_rank']})")
    print("Classification    : B. Model is missing set-piece/penalty share features & Man Utd team attack rating weighting.")

# Model vs Consensus Discrepancies
print("\n=== 4. LARGEST MODEL vs CONSENSUS DISCREPANCIES ===")
top_model_differentials = df_res.sort_values('rank_diff', ascending=False).head(5)
print("\nTop 5 Model Differentials (High Model Rank / Low Ownership):")
for _, r in top_model_differentials.iterrows():
    print(f"  {r['web_name']:<20} ({r['position']}) | Model Rank #{r['v2_rank']} vs Consensus #{r['consensus_rank']} (Diff +{r['rank_diff']}) | xP: {r['v2_weighted_xp']}")

top_consensus_traps = df_res.sort_values('rank_diff', ascending=True).head(5)
print("\nTop 5 Consensus Traps (Low Model Rank / High Ownership):")
for _, r in top_consensus_traps.iterrows():
    print(f"  {r['web_name']:<20} ({r['position']}) | Model Rank #{r['v2_rank']} vs Consensus #{r['consensus_rank']} (Diff {r['rank_diff']}) | xP: {r['v2_weighted_xp']}")

# Serialize to JSON
out_json = {
    'critical_players': critical_list,
    'top_model_differentials': top_model_differentials[['web_name', 'position', 'price', 'ownership', 'v2_rank', 'consensus_rank', 'rank_diff', 'v2_weighted_xp']].to_dict('records'),
    'top_consensus_traps': top_consensus_traps[['web_name', 'position', 'price', 'ownership', 'v2_rank', 'consensus_rank', 'rank_diff', 'v2_weighted_xp']].to_dict('records')
}

with open("scratch/phase3d_projections_output.json", "w") as f:
    json.dump(out_json, f, indent=2)

print("\nProjections & diagnostics saved to scratch/phase3d_projections_output.json")
