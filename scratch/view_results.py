import json

with open('scratch/prediction_reality_check_output.json') as f:
    d = json.load(f)

print("=== OVERALL METRICS ===")
print(json.dumps(d['overall_metrics'], indent=2))

print("\n=== POSITION BREAKDOWN ===")
print(json.dumps(d['position_breakdown'], indent=2))

print("\n=== PRICE BREAKDOWN ===")
print(json.dumps(d['price_breakdown'], indent=2))

print("\n=== MINUTES BUCKET BREAKDOWN ===")
print(json.dumps(d['minutes_breakdown'], indent=2))

print("\n=== ESTABLISHED BREAKDOWN ===")
print(json.dumps(d['established_breakdown'], indent=2))

print("\n=== CALIBRATION P(START) ===")
print(json.dumps(d['calibration_pstart'], indent=2))

print("\n=== CALIBRATION CLEAN SHEET ===")
print(json.dumps(d['calibration_cs'], indent=2))

print("\n=== PLAYER SANITY CHECK ===")
for ps in d['player_sanity_check']:
    print(f"{ps['name']:<22} | N={ps['count']:<4} | pred_xP={ps['mean_pred_xP']:.2f} | act_pts={ps['mean_actual_pts']:.2f} | xP_MAE={ps['mae_xp']:.2f} | xP_r={ps['pearson_r']:.3f} | xP_rho={ps['spearman_rho']:.3f}")

print("\n=== CURRENT 2026/27 SNAPSHOT ===")
for p in d['snapshot_2026_27']:
    print(f"{p['web_name']:<20} | Pos: {p['position']} | Price: {p['price']} | Fix: {p['fixture']} | xMins: {p['expected_minutes']}m | pStart: {p['p_start']:.2f} | xG: {p['xg_match']:.2f} | xA: {p['xa_match']:.2f} | CS: {p['cs_prob']:.2f} | GW1: {p['gw1_xp']} xP | 4GW: {p['weighted_4gw']} xP")
