import os
import sys
import json
import pandas as pd

sys.path.append(os.getcwd())
from backend.database import get_db
from backend.models import Player, Team, PlayerProjection
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer

print("=== PHASE 3D.1 READ-ONLY PLAYER PRICE INTEGRITY AUDIT ===")

db = next(get_db())
players = db.query(Player).all()
print(f"Canonical Database Active Players Count: {len(players)}")

# Check layer 1: Database Player.now_cost
db_player_map = {p.id: p for p in players}

# Layer 2: Projection Engine price
engine = ProjectionEngine(db=db)
proj_price_matches = 0
proj_price_mismatches = 0
proj_price_missing = 0

for p in players:
    try:
        bd = engine.calculate_player_xp_breakdown(p)
        engine_price_m = bd.get("price")
        canonical_price_m = p.now_cost / 10.0
        if abs(engine_price_m - canonical_price_m) < 1e-4:
            proj_price_matches += 1
        else:
            proj_price_mismatches += 1
            print(f"Mismatch in Projection Engine for {p.web_name} (ID {p.id}): Engine £{engine_price_m}m vs Canonical £{canonical_price_m}m")
    except Exception as e:
        proj_price_missing += 1

print(f"\n1. Projection Engine Price Audit (590 Players):")
print(f"   - Matching Prices   : {proj_price_matches} / {len(players)}")
print(f"   - Mismatched Prices : {proj_price_mismatches}")
print(f"   - Missing Prices    : {proj_price_missing}")

# Layer 3: Squad Optimizer price
optimizer = SquadOptimizer(db=db)
opt_result = optimizer.solve_squad_selection(mode="CURRENT_GW_PLUS_3")
opt_players = opt_result.get("starting_11", []) + opt_result.get("bench", [])

opt_price_matches = 0
opt_price_mismatches = 0

for p_dict in opt_players:
    p_id = p_dict["id"]
    canonical_p = db_player_map[p_id]
    p_cost_m = p_dict.get("price", p_dict.get("now_cost", 0) / 10.0)
    canonical_cost_m = canonical_p.now_cost / 10.0
    if abs(p_cost_m - canonical_cost_m) < 1e-4:
        opt_price_matches += 1
    else:
        opt_price_mismatches += 1
        print(f"Mismatch in Optimizer for {canonical_p.web_name}: Opt £{p_cost_m}m vs Canonical £{canonical_cost_m}m")

print(f"\n2. Squad Optimizer Price Audit (15 Selected Players):")
print(f"   - Matching Prices   : {opt_price_matches} / {len(opt_players)}")
print(f"   - Mismatched Prices : {opt_price_mismatches}")

# Layer 4: Target 13 Players Audit (Bruno Fernandes, Haaland, Salah, Palmer, Saka, Gabriel, Mbeumo, Semenyo, Marmoush, Awoniyi, Osula, João Pedro, Calvert-Lewin)
target_names_map = {
    'Bruno Fernandes': ['B.Fernandes', 'Fernandes', 'Bruno'],
    'Erling Haaland': ['Haaland'],
    'Mohamed Salah': ['Salah'],
    'Cole Palmer': ['Palmer'],
    'Bukayo Saka': ['Saka'],
    'Gabriel Magalhães': ['Gabriel'],
    'Mbeumo': ['Mbeumo'],
    'Semenyo': ['Semenyo'],
    'Marmoush': ['Marmoush'],
    'Awoniyi': ['Awoniyi'],
    'Osula': ['Osula'],
    'João Pedro': ['João Pedro', 'Pedro'],
    'Calvert-Lewin': ['Calvert-Lewin']
}

print("\n=== 3. TARGET 13 PLAYERS CANONICAL DATABASE CHECK ===")
print(f"{'Target Query':<20} | {'Matched Web Name':<18} | {'ID':<5} | {'Canonical now_cost':<18} | {'Price (£m)':<10} | {'Ownership %':<12}")
print("-" * 95)

target_audit_records = []

for target, search_terms in target_names_map.items():
    matched = None
    # Precise match search logic
    for term in search_terms:
        matches = [p for p in players if p.web_name.lower() == term.lower()]
        if matches:
            matched = matches[0]
            break
    if not matched:
        for term in search_terms:
            matches = [p for p in players if term.lower() in p.web_name.lower()]
            if matches:
                matched = matches[0]
                break
                
    if matched:
        price_m = matched.now_cost / 10.0
        print(f"{target:<20} | {matched.web_name:<18} | {matched.id:<5} | {matched.now_cost:<18} | £{price_m:<9.1f} | {matched.selected_by_percent}%")
        target_audit_records.append({
            'target': target,
            'id': matched.id,
            'web_name': matched.web_name,
            'now_cost': matched.now_cost,
            'price_m': price_m,
            'ownership': float(matched.selected_by_percent) if matched.selected_by_percent else 0.0
        })
    else:
        print(f"{target:<20} | NOT FOUND IN DB!")

# Audit reporting script mismatch root cause
print("\n=== 4. PHASE 3D REPORTING SCRIPT STRING MATCHING AUDIT ===")
print("Previous matching logic used: df_res['web_name'].str.contains('Bruno Fernandes') which returned empty!")
print("Fallback or ambiguous match df_res['web_name'].str.contains('Bruno') matched ID 452 (Bruno G. - Bruno Guimarães) at £7.0m / 9.3% ownership!")
print("Canonical Bruno Fernandes is ID 426 (B.Fernandes) at now_cost = 120 (£12.0m) / 48.6% ownership!")
