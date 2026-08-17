import logging
from backend.database import SessionLocal
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.models import Player, Fixture, Team

logging.basicConfig(level=logging.INFO)

def run_verification():
    db = SessionLocal()
    try:
        print("=== 1. RUNNING FIXTURE-AWARE PROJECTION ENGINE (GW1 - GW4) ===")
        proj_engine = ProjectionEngine(db)
        updated = proj_engine.run_projections(start_gw=1, end_gw=4, source="internal")
        print(f"Updated {updated} player projections across GW1-GW4.")

        print("\n=== 2. EXAMPLE PLAYERS: GW0–GW3 FIXTURE & xP BREAKDOWN ===")
        example_players = db.query(Player).filter(Player.web_name.in_(["Saka", "Haaland", "Gabriel", "Palmer"])).all()
        teams_map = {t.id: t for t in db.query(Team).all()}
        
        horizon_gws = [1, 2, 3, 4]
        for p in example_players:
            print(f"\nPlayer: {p.web_name} ({p.element_type} - £{p.now_cost/10.0:.1f}m)")
            for gw in horizon_gws:
                fixtures = db.query(Fixture).filter(Fixture.event_id == gw).all()
                p_fix = []
                for f in fixtures:
                    if f.team_h_id == p.team_id:
                        p_fix.append((f, True, teams_map.get(f.team_a_id)))
                    elif f.team_a_id == p.team_id:
                        p_fix.append((f, False, teams_map.get(f.team_h_id)))
                
                if p_fix:
                    f, is_home, opp_team = p_fix[0]
                    bd = proj_engine.calculate_player_xp_breakdown(p, f, is_home, opp_team)
                    print(f"  GW{gw}: vs {bd['opponent']} | xMins: {bd['xMins']} | xG: {bd['xg_match']} | xA: {bd['xa_match']} | CS Prob: {bd['cs_prob']} | DEFCON Prob: {bd['defcon_prob']} | Total xP: {bd['total_xp']}")
                else:
                    print(f"  GW{gw}: BLANK / BYE | xP: 0.0")

        print("\n=== 3. RUNNING OPTIMIZER ON REAL DATABASE ===")
        optimizer = SquadOptimizer(db)
        res = optimizer.solve_squad_selection(mode="CURRENT_GW_PLUS_3", current_gw=1, total_budget=1000)

        print(f"Model Version: {res.get('model_version')}")
        print(f"Optimization Mode: {res.get('optimization_mode')}")
        print(f"Horizon Weights: {res.get('horizon_weights')} (GW1=55%, GW2=20%, GW3=15%, GW4=10%)")
        print(f"Total Budget Used: {res['total_cost_str']} / £100.0m (Bank: {res['bank_str']})")
        print(f"Current GW Starting XI xP: {res['current_gw_starting_xi_xp']} (+{res['captain_contribution_xp']} Cap Bonus = Total {res['total_current_gw_xp']})")
        print(f"4-GW Weighted Squad Score: {res['weighted_horizon_xp']}")
        print(f"Captain: {res['captain']['web_name']} ({res['captain']['element_type']} - {res['captain']['now_cost_str']})")
        print(f"Vice-Captain: {res['vice_captain']['web_name']}")

        print("\nOptimal Starting XI (Current GW1 Focus):")
        for p in res["starting_11"]:
            cap_str = " (C)" if p["is_captain"] else (" (V)" if p["is_vice_captain"] else "")
            print(f"  {p['element_type']} | {p['web_name']} ({p['team_name']}) - {p['now_cost_str']} | GW0 xP: {p['gw0_xp']} | 4-GW Weighted: {p['weighted_xp']} xP{cap_str}")

        print("\nBench:")
        for p in res["bench"]:
            print(f"  {p['element_type']} | {p['web_name']} ({p['team_name']}) - {p['now_cost_str']} | GW0 xP: {p['gw0_xp']} | 4-GW Weighted: {p['weighted_xp']} xP")

        print("\nExplanations:")
        for e in res["explanations"]:
            print(f"  [Info] {e}")

    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
