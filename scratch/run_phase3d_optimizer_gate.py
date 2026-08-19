import os
import sys
import json

sys.path.append(os.getcwd())
from backend.database import get_db
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.projections.engine import ProjectionEngine

print("=== RUNNING OPTIMIZER GATE ON FRESH DEPLOYED V2 PROJECTIONS ===")

db = next(get_db())
engine = ProjectionEngine(db=db)
optimizer = SquadOptimizer(db=db)

modes = ["CURRENT_GW_PLUS_3", "STRONG_XI_DUMP_BENCH", "BALANCED_BENCH", "MAXIMUM_SQUAD"]
opt_results = {}

for mode in modes:
    print(f"\nRunning Optimization Mode: {mode}")
    result = optimizer.solve_squad_selection(mode=mode)
    starting_xi = result.get('starting_11', [])
    bench = result.get('bench', [])
    cap_name = result.get('captain', {}).get('web_name', 'N/A') if isinstance(result.get('captain'), dict) else 'N/A'
    
    cost = result.get('total_cost', 1000) / 10.0
    bank = result.get('bank', 0) / 10.0
    gw0_xp = result.get('total_current_gw_xp', 0.0)
    weighted_xp = result.get('weighted_horizon_xp', 0.0)
    
    print(f"  Squad Cost       : £{cost:.1f}m (Bank: £{bank:.1f}m)")
    print(f"  GW0 XI xP        : {gw0_xp:.2f}")
    print(f"  4-GW Weighted xP : {weighted_xp:.2f}")
    print(f"  Captain Pick     : {cap_name}")
    print(f"  Starters ({len(starting_xi)}): {', '.join([p.get('web_name', '') for p in starting_xi])}")
    print(f"  Bench ({len(bench)}): {', '.join([p.get('web_name', '') for p in bench])}")
    
    opt_results[mode] = {
        'total_cost': cost,
        'bank': bank,
        'gw0_xp': gw0_xp,
        'weighted_xp': weighted_xp,
        'captain': cap_name,
        'starters': [p.get('web_name', '') for p in starting_xi],
        'bench': [p.get('web_name', '') for p in bench]
    }

with open("scratch/phase3d_optimizer_gate_output.json", "w") as f:
    json.dump(opt_results, f, indent=2)

print("\nOptimizer Gate execution completed successfully. Results saved to scratch/phase3d_optimizer_gate_output.json")
