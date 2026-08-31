import sys, os
sys.path.insert(0, os.getcwd())
from backend.database import SessionLocal
from backend.services.fpl_history_service import FPLHistoryService

db = SessionLocal()
service = FPLHistoryService(db)
snap1 = service.get_gameweek_snapshot(gw=1)

print("GW1 Bench Players points breakdown:")
for p in snap1['bench']:
    print(f"{p['web_name']} ({p['position']}): actual_pts={p.get('actual_pts')}, multiplier={p.get('multiplier')}, effective_mult={p.get('effective_multiplier')}")
