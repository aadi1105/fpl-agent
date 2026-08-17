from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.projections.engine import ProjectionEngine

def run_audit():
    db = SessionLocal()
    try:
        engine = ProjectionEngine(db)
        names = ["Haaland", "Awoniyi", "Palmer", "O'Riley"]

        players = db.query(Player).filter(Player.web_name.in_(names)).all()
        teams_map = {t.id: t for t in db.query(Team).all()}

        print("=== PROJECTION COMPONENT SANITY AUDIT (GW1 Focus) ===\n")

        for p in players:
            team = teams_map.get(p.team_id)
            fixtures = db.query(Fixture).filter(Fixture.event_id == 1).all()
            p_fix = None
            for f in fixtures:
                if f.team_h_id == p.team_id:
                    p_fix = (f, True, teams_map.get(f.team_a_id))
                    break
                elif f.team_a_id == p.team_id:
                    p_fix = (f, False, teams_map.get(f.team_h_id))
                    break

            if not p_fix:
                continue

            f, is_home, opp_team = p_fix
            bd = engine.calculate_player_xp_breakdown(p, f, is_home, opp_team)
            
            raw_sum = (
                bd["appearance_xp"] + bd["goals_xp"] + bd["assists_xp"] +
                bd["cs_xp"] + bd["defcon_xp"] + bd["saves_xp"] +
                bd["bonus_xp"] + bd["cards_xp"]
            )

            print(f"--- PLAYER: {bd['web_name']} ({bd['position']} - {bd['price_str']} - Team: {team.short_name if team else ''}) ---")
            print(f"  Raw Record: mins={p.minutes}, xG={p.expected_goals}, xA={p.expected_assists}, BPS={p.bps}, Cost={p.now_cost}")
            print(f"  Fixture: vs {bd['opponent']}")
            print(f"  Expected Minutes (xMins): {bd['xMins']}")
            print(f"  Match xG: {bd['xg_match']:.4f} | Goal Pts: {bd['goals_xp']:.4f}")
            print(f"  Match xA: {bd['xa_match']:.4f} | Assist Pts: {bd['assists_xp']:.4f}")
            print(f"  Appearance Pts: {bd['appearance_xp']:.4f}")
            print(f"  CS Prob: {bd['cs_prob']:.4f} | CS Pts: {bd['cs_xp']:.4f}")
            print(f"  DEFCON Prob: {bd['defcon_prob']:.4f} | DEFCON Pts: {bd['defcon_xp']:.4f}")
            print(f"  Bonus Pts: {bd['bonus_xp']:.4f}")
            print(f"  Cards Pts: {bd['cards_xp']:.4f}")
            print(f"  Exact Component Sum: {raw_sum:.4f} => Total xP: {bd['total_xp']:.2f}\n")

    finally:
        db.close()

if __name__ == "__main__":
    run_audit()
