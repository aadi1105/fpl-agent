from backend.database import SessionLocal
from backend.projections.team_ratings import TeamRatingCalculator

def run_test():
    db = SessionLocal()
    try:
        calc = TeamRatingCalculator(db)
        ratings = calc.calculate_and_update_team_ratings()
        print(f"Calculated Team Ratings for {len(ratings)} teams:\n")
        print(f"{'Team':<6} | {'Att (H)':<8} | {'Att (A)':<8} | {'Def (H)':<8} | {'Def (A)':<8}")
        print("-" * 50)
        for t_id, r in sorted(ratings.items(), key=lambda x: x[1]['att_h'], reverse=True):
            print(f"{r['short_name']:<6} | {r['att_h']:<8.1f} | {r['att_a']:<8.1f} | {r['def_h']:<8.1f} | {r['def_a']:<8.1f}")

    finally:
        db.close()

if __name__ == "__main__":
    run_test()
