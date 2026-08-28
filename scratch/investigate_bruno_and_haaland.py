import os
import sys
import json
import pandas as pd

sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.projections.engine import ProjectionEngine

db = SessionLocal()
engine = ProjectionEngine(db=db)

players_to_check = ["Haaland", "O'Reilly", "Calafiori", "Gvardiol", "B.Fernandes", "Saka", "Palmer", "Awoniyi"]

print("==========================================================================================")
print("FORENSIC COMPARISON: WHY DEFENDERS / MIDFIELDERS RANK ABOVE HAALAND & BRUNO FERNANDES AUDIT")
print("==========================================================================================\n")

for name in players_to_check:
    p = db.query(Player).filter(Player.web_name.ilike(f"%{name}%")).first()
    if not p:
        continue
    
    p_team = db.query(Team).filter(Team.id == p.team_id).first()
    fix1 = db.query(Fixture).filter(
        ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
        Fixture.event_id == 1
    ).first()
    
    if fix1:
        is_home = (fix1.team_h_id == p.team_id)
        opp_id = fix1.team_a_id if is_home else fix1.team_h_id
        opp_team = db.query(Team).filter(Team.id == opp_id).first()
        bd = engine.calculate_player_xp_breakdown(p, fixture=fix1, is_home=is_home, opp_team=opp_team)
    else:
        bd = {}
        
    print(f"--- {p.web_name} ({p.element_type}, {p_team.short_name}, £{p.now_cost/10.0:.1f}m) vs {bd.get('opponent','N/A')} ---")
    print(f"  Expected Minutes : {bd.get('xMins',0.0):.1f}m | pStart: {bd.get('p_start',0.0):.2f}")
    print(f"  Match xG         : {bd.get('xg_match',0.0):.4f} (Goal Multiplier: {bd.get('goals_multiplier',0)}) -> Goals xP: {bd.get('goals_xp',0.0):.2f}")
    print(f"  Match xA         : {bd.get('xa_match',0.0):.4f} (Assist Multiplier: 3.0) -> Assists xP: {bd.get('assists_xp',0.0):.2f}")
    print(f"  Clean Sheet Prob : {bd.get('cs_prob',0.0):.4f} (CS Multiplier: {bd.get('cs_multiplier',0)}) -> CS xP: {bd.get('cs_xp',0.0):.2f}")
    print(f"  DEFCON Prob      : {bd.get('defcon_prob',0.0):.4f} -> DEFCON xP: {bd.get('defcon_xp',0.0):.2f}")
    print(f"  Appearance xP    : {bd.get('appearance_xp',0.0):.2f}")
    print(f"  Bonus xP         : {bd.get('bonus_xp',0.0):.2f}")
    print(f"  Yellow Cards xP  : {bd.get('cards_xp',0.0):.2f}")
    print(f"  TOTAL GW1 xP     : {bd.get('total_xp',0.0):.2f} pts\n")

db.close()
