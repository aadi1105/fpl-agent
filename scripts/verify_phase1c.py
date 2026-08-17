from backend.database import SessionLocal
from backend.models import Player, Team, Fixture
from backend.projections.engine import ProjectionEngine
from backend.projections.team_ratings import TeamRatingCalculator

def run_validation():
    db = SessionLocal()
    try:
        print("=== PHASE 1C: TEAM RATINGS & FIXTURE DIFFICULTY VALIDATION TABLE ===\n")
        calc = TeamRatingCalculator(db)
        calc.calculate_and_update_team_ratings()

        engine = ProjectionEngine(db)
        engine.run_projections(start_gw=1, end_gw=4, source="internal")

        teams_by_name = {t.short_name: t for t in db.query(Team).all()}
        
        mci = teams_by_name.get("MCI")
        ars = teams_by_name.get("ARS")
        sun = teams_by_name.get("SUN")
        bou = teams_by_name.get("BOU")

        print("--- 1. TEAM STRENGTH RATINGS SUMMARY ---")
        print(f"Man City (MCI)   - Att H: {mci.strength_attack_home:<6.1f} | Att A: {mci.strength_attack_away:<6.1f} | Def H: {mci.strength_defence_home:<6.1f} | Def A: {mci.strength_defence_away:<6.1f}")
        print(f"Arsenal (ARS)    - Att H: {ars.strength_attack_home:<6.1f} | Att A: {ars.strength_attack_away:<6.1f} | Def H: {ars.strength_defence_home:<6.1f} | Def A: {ars.strength_defence_away:<6.1f}")
        print(f"Bournemouth(BOU) - Att H: {bou.strength_attack_home:<6.1f} | Att A: {bou.strength_attack_away:<6.1f} | Def H: {bou.strength_defence_home:<6.1f} | Def A: {bou.strength_defence_away:<6.1f}")
        print(f"Sunderland (SUN) - Att H: {sun.strength_attack_home:<6.1f} | Att A: {sun.strength_attack_away:<6.1f} | Def H: {sun.strength_defence_home:<6.1f} | Def A: {sun.strength_defence_away:<6.1f}\n")

        # Pick key players for difficulty scenario test:
        # Haaland (MCI FWD)
        # Saka (ARS MID)
        # Gabriel (ARS DEF)
        # Ballard (SUN DEF)
        haaland = db.query(Player).filter(Player.web_name == "Haaland").first()
        gabriel = db.query(Player).filter(Player.web_name == "Gabriel").first()

        print("--- 2. FIXTURE DIFFICULTY SCENARIOS (ATTACKERS) ---")
        print(f"{'Scenario':<42} | {'Player':<8} | {'Fixture':<10} | {'Opp Def Rating':<14} | {'Att Modifier':<12} | {'xG':<6} | {'Total xP':<8}")
        print("-" * 115)

        # Scenario A: Strong Attack vs Weak Defence (Haaland vs Bournemouth Home)
        bd_a = engine.calculate_player_xp_breakdown(haaland, None, True, bou)
        print(f"{'Strong Attack vs Weak Defence':<42} | {haaland.web_name:<8} | {bd_a['opponent']:<10} | {bd_a['opp_defence_rating']:<14.1f} | {bd_a['fixture_attack_modifier']:<12.3f} | {bd_a['xg_match']:<6.3f} | {bd_a['total_xp']:<8.2f}")

        # Scenario B: Strong Attack vs Elite Defence (Haaland vs Arsenal Away)
        bd_b = engine.calculate_player_xp_breakdown(haaland, None, False, ars)
        print(f"{'Strong Attack vs Elite Defence':<42} | {haaland.web_name:<8} | {bd_b['opponent']:<10} | {bd_b['opp_defence_rating']:<14.1f} | {bd_b['fixture_attack_modifier']:<12.3f} | {bd_b['xg_match']:<6.3f} | {bd_b['total_xp']:<8.2f}")

        print("\n--- 3. FIXTURE DIFFICULTY SCENARIOS (DEFENDERS / CLEAN SHEETS) ---")
        print(f"{'Scenario':<42} | {'Player':<8} | {'Fixture':<10} | {'Opp Att Rating':<14} | {'CS Ratio':<12} | {'CS Prob':<7} | {'Total xP':<8}")
        print("-" * 115)

        # Scenario C: Elite Defence vs Weak Attack (Gabriel vs Sunderland Home)
        bd_c = engine.calculate_player_xp_breakdown(gabriel, None, True, sun)
        print(f"{'Elite Defence vs Weak Attack':<42} | {gabriel.web_name:<8} | {bd_c['opponent']:<10} | {bd_c['opp_attack_rating']:<14.1f} | {bd_c['fixture_defence_modifier']:<12.3f} | {bd_c['cs_prob']:<7.3f} | {bd_c['total_xp']:<8.2f}")

        # Scenario D: Elite Defence vs Strong Attack (Gabriel vs Man City Away)
        bd_d = engine.calculate_player_xp_breakdown(gabriel, None, False, mci)
        print(f"{'Elite Defence vs Strong Attack':<42} | {gabriel.web_name:<8} | {bd_d['opponent']:<10} | {bd_d['opp_attack_rating']:<14.1f} | {bd_d['fixture_defence_modifier']:<12.3f} | {bd_d['cs_prob']:<7.3f} | {bd_d['total_xp']:<8.2f}")

    finally:
        db.close()

if __name__ == "__main__":
    run_validation()
