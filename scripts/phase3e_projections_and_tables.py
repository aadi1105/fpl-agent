import os
import sys
import json
import csv
import pandas as pd
from datetime import datetime

sys.path.append(os.getcwd())
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture, Gameweek
from backend.projections.engine import ProjectionEngine

def run_phase3e_projections():
    print("==================================================")
    print("PHASE 3E — PROJECTIONS & DATA INTEGRITY SNAPSHOT")
    print("==================================================\n")

    db = SessionLocal()
    try:
        engine = ProjectionEngine(db=db)
        
        # 1. GW1-GW4 Club Fixture Snapshot
        print("Step 1: Building GW1-GW4 Club Fixture Snapshot...")
        teams = db.query(Team).order_by(Team.name).all()
        club_snapshot = []
        
        for t in teams:
            row = {'club_id': t.id, 'club_name': t.name, 'short_name': t.short_name}
            for gw in range(1, 5):
                fix = db.query(Fixture).filter(
                    ((Fixture.team_h_id == t.id) | (Fixture.team_a_id == t.id)),
                    Fixture.event_id == gw
                ).first()
                if fix:
                    is_home = (fix.team_h_id == t.id)
                    opp_id = fix.team_a_id if is_home else fix.team_h_id
                    opp_team = db.query(Team).filter(Team.id == opp_id).first()
                    opp_name = opp_team.short_name if opp_team else "OPP"
                    row[f"gw{gw}_fixture"] = f"{opp_name} ({'H' if is_home else 'A'})"
                else:
                    row[f"gw{gw}_fixture"] = "BLANK"
            club_snapshot.append(row)

        # 2. Critical Player Sanity Check Table
        print("Step 2: Building Critical Player Data Sanity Check Table...")
        target_names = [
            "Haaland", "Bruno Fernandes", "Saka", "Palmer", "Gabriel",
            "João Pedro", "Calvert-Lewin", "Awoniyi", "Osula", "Marmoush",
            "Beto", "Nelson"
        ]
        
        player_sanity_table = []
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

            team = db.query(Team).filter(Team.id == p.team_id).first()
            p_row = {
                'player_id': p.id,
                'player_name': f"{p.first_name} {p.second_name} ({p.web_name})",
                'current_club': f"{team.name} ({team.short_name})",
                'price': f"£{p.now_cost / 10.0:.1f}m",
                'status': p.status,
                'chance_of_playing': p.chance_of_playing_next_round if p.chance_of_playing_next_round is not None else 100
            }

            for gw in range(1, 5):
                fix = db.query(Fixture).filter(
                    ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                    Fixture.event_id == gw
                ).first()
                if fix:
                    is_home = (fix.team_h_id == p.team_id)
                    opp_id = fix.team_a_id if is_home else fix.team_h_id
                    opp_team = db.query(Team).filter(Team.id == opp_id).first()
                    opp_name = opp_team.short_name if opp_team else "OPP"
                    p_row[f"gw{gw}_fixture"] = f"{opp_name} ({'H' if is_home else 'A'})"
                else:
                    p_row[f"gw{gw}_fixture"] = "BLANK"

            player_sanity_table.append(p_row)

        # 3. Regenerate GW1-GW4 Projections across All Active Players
        print("Step 3: Regenerating GW1-GW4 projections across all active players...")
        active_players = db.query(Player).filter(Player.status == "a").all()
        all_projections = []

        for p in active_players:
            p_team = db.query(Team).filter(Team.id == p.team_id).first()
            
            # GW1 Fixture
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
                bd = {
                    "opponent": "BLANK", "xMins": 0.0, "p_start": 0.0,
                    "xg_match": 0.0, "xa_match": 0.0, "cs_prob": 0.0, "total_xp": 0.0
                }

            gw1_xp = bd['total_xp']
            gw2_xp = round(gw1_xp * 0.95, 2)
            gw3_xp = round(gw1_xp * 0.90, 2)
            gw4_xp = round(gw1_xp * 0.85, 2)
            weighted_4gw = round(0.55 * gw1_xp + 0.20 * gw2_xp + 0.15 * gw3_xp + 0.10 * gw4_xp, 2)

            all_projections.append({
                'id': p.id,
                'web_name': p.web_name,
                'full_name': f"{p.first_name} {p.second_name}",
                'position': p.element_type,
                'team_id': p.team_id,
                'team_name': p_team.name,
                'team_short': p_team.short_name,
                'price': p.now_cost / 10.0,
                'price_str': f"£{p.now_cost / 10.0:.1f}m",
                'gw1_fixture': bd.get('opponent', 'BLANK'),
                'expected_minutes': bd.get('xMins', 0.0),
                'p_start': bd.get('p_start', 0.0),
                'xg_match': bd.get('xg_match', 0.0),
                'xa_match': bd.get('xa_match', 0.0),
                'cs_prob': bd.get('cs_prob', 0.0),
                'gw1_xp': gw1_xp,
                'gw2_xp': gw2_xp,
                'gw3_xp': gw3_xp,
                'gw4_xp': gw4_xp,
                'weighted_4gw': weighted_4gw
            })

        df_proj = pd.DataFrame(all_projections)
        df_ranked_gw1 = df_proj.sort_values(by='gw1_xp', ascending=False).reset_index(drop=True)

        results_data = {
            'sync_timestamp': datetime.utcnow().isoformat() + "Z",
            'club_snapshot': club_snapshot,
            'player_sanity_table': player_sanity_table,
            'top_ranked_gw1': df_ranked_gw1.head(30).to_dict(orient='records')
        }

        os.makedirs("scratch", exist_ok=True)
        with open("scratch/phase3e_audit_output.json", "w") as f:
            json.dump(results_data, f, indent=2)

        print("\n==================================================")
        print("TOP 20 RANKED GW1 PLAYERS AFTER PHASE 3E DATA FIX")
        print("==================================================")
        for idx, row in df_ranked_gw1.head(20).iterrows():
            print(f"{idx+1:2d}. {row['web_name']:<18} ({row['position']}, {row['team_short']}, {row['price_str']}) | Fix: {row['gw1_fixture']:<12} | xMins: {row['expected_minutes']:<4.1f}m | pStart: {row['p_start']:.2f} | xG: {row['xg_match']:.2f} | xA: {row['xa_match']:.2f} | CS: {row['cs_prob']:.2f} | GW1: {row['gw1_xp']} xP")
        print("==================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    run_phase3e_projections()
