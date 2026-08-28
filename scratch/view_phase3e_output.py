import json

with open("scratch/phase3e_audit_output.json") as f:
    d = json.load(f)

print("=== CRITICAL PLAYER DATA SANITY CHECK TABLE ===")
print(f"{'Player Name':<28} | {'Current Club':<20} | {'Price':<6} | {'Status':<6} | {'Playing %':<9} | {'GW1':<10} | {'GW2':<10} | {'GW3':<10} | {'GW4':<10}")
print("-" * 125)
for p in d['player_sanity_table']:
    print(f"{p['player_name']:<28} | {p['current_club']:<20} | {p['price']:<6} | {p['status']:<6} | {p['chance_of_playing']:<9}% | {p['gw1_fixture']:<10} | {p['gw2_fixture']:<10} | {p['gw3_fixture']:<10} | {p['gw4_fixture']:<10}")

print("\n=== GW1-GW4 CLUB FIXTURE SNAPSHOT ===")
print(f"{'Club Name':<22} | {'Short':<5} | {'GW1 Fixture':<12} | {'GW2 Fixture':<12} | {'GW3 Fixture':<12} | {'GW4 Fixture':<12}")
print("-" * 90)
for c in d['club_snapshot']:
    print(f"{c['club_name']:<22} | {c['short_name']:<5} | {c['gw1_fixture']:<12} | {c['gw2_fixture']:<12} | {c['gw3_fixture']:<12} | {c['gw4_fixture']:<12}")
