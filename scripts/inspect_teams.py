from backend.database import SessionLocal
from backend.models import Team, Fixture, Player

def inspect_data():
    db = SessionLocal()
    try:
        teams = db.query(Team).all()
        print(f"Total Teams: {len(teams)}")
        for t in teams[:5]:
            print(f"ID: {t.id}, Name: {t.name}, Short: {t.short_name}, Att H: {t.strength_attack_home}, Att A: {t.strength_attack_away}, Def H: {t.strength_defence_home}, Def A: {t.strength_defence_away}")

        fixtures = db.query(Fixture).all()
        print(f"Total Fixtures: {len(fixtures)}")

        # Check aggregated player xG/xGA per team to see if team stats can be derived from player totals
        for t in teams[:10]:
            players = db.query(Player).filter(Player.team_id == t.id).all()
            tot_xg = sum(p.expected_goals for p in players)
            tot_xga = sum(p.expected_goals_conceded for p in players)
            tot_mins = sum(p.minutes for p in players)
            print(f"Team {t.short_name}: total xG={tot_xg:.2f}, total xGA={tot_xga:.2f}, max player mins={max((p.minutes for p in players), default=0)}")

    finally:
        db.close()

if __name__ == "__main__":
    inspect_data()
