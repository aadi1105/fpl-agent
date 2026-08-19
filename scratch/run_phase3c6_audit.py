import sys
import json
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Player, Team, Fixture, Gameweek
from backend.projections.engine import ProjectionEngine
from backend.ml.minutes_predictor import MinutesPredictor

TARGET_NAMES = [
    "Awoniyi", "Osula", "Marmoush", "Beto",
    "Haaland", "Isak", "Watkins", "Solanke", "Wood",
    "João Pedro", "Calvert-Lewin"
]

def run_audit():
    db: Session = SessionLocal()
    engine = ProjectionEngine(db)
    
    # Get GW1 fixtures map
    gw1_fixtures = db.query(Fixture).filter(Fixture.event_id == 1).all()
    teams_map = {t.id: t for t in db.query(Team).all()}
    
    results = {}
    
    for name in TARGET_NAMES:
        # Search player
        player = db.query(Player).filter(Player.web_name.ilike(f"%{name}%")).first()
        if not player:
            print(f"NOT FOUND: {name}")
            continue
            
        # Find GW1 fixture
        fix = db.query(Fixture).filter(
            Fixture.event_id == 1,
            (Fixture.team_h_id == player.team_id) | (Fixture.team_a_id == player.team_id)
        ).first()
        
        is_home = fix.team_h_id == player.team_id if fix else True
        opp_team_id = (fix.team_a_id if is_home else fix.team_h_id) if fix else 1
        opp_team = teams_map.get(opp_team_id)
        
        # Calculate full breakdown
        breakdown = engine.calculate_player_xp_breakdown(player, fix, is_home, opp_team)
        
        # Also inspect per_90 metrics
        metrics = engine.get_player_per_90_metrics(player)
        
        # Also inspect raw input pdata to minutes_predictor
        tot_mins = float(player.minutes)
        recent_mins_5 = float(min(450.0, tot_mins))
        recent_apps_5 = float(min(5.0, tot_mins / 60.0)) if tot_mins > 0 else 0.0
        recent_starts_5 = float(min(5.0, tot_mins / 80.0)) if tot_mins >= 80 else 0.0
        avg_mins_5 = float(recent_mins_5 / max(1.0, recent_apps_5)) if recent_apps_5 > 0 else 0.0
        diff = (fix.team_a_difficulty if is_home else fix.team_h_difficulty) if fix else 3
        
        pdata = {
            'price': player.now_cost / 10.0,
            'fixture_difficulty': diff,
            'team_attack_rating': player.team.strength_attack_home if is_home else player.team.strength_attack_away,
            'team_defence_rating': player.team.strength_defence_home if is_home else player.team.strength_defence_away,
            'opponent_attack_rating': opp_team.strength_attack_away if is_home else opp_team.strength_attack_home,
            'opponent_defence_rating': opp_team.strength_defence_away if is_home else opp_team.strength_defence_home,
            'home_away_is_home': 1.0 if is_home else 0.0,
            'minutes_last_1': float(min(90.0, avg_mins_5)),
            'minutes_last_3': float(min(270.0, recent_mins_5 * 0.6)),
            'minutes_last_5': recent_mins_5,
            'minutes_last_10': float(min(900.0, tot_mins)),
            'starts_last_1': 1.0 if recent_starts_5 >= 1.0 else 0.0,
            'starts_last_3': float(min(3.0, recent_starts_5 * 0.6)),
            'starts_last_5': recent_starts_5,
            'starts_last_10': float(min(10.0, tot_mins / 80.0)),
            'appearances_last_5': recent_apps_5,
            'bench_appearances_last_5': float(max(0.0, recent_apps_5 - recent_starts_5)),
            'unused_substitute_last_5': float(max(0.0, 5.0 - recent_apps_5)),
            'average_minutes_last_5': avg_mins_5,
            'average_minutes_last_10': avg_mins_5,
            'days_since_last_match': 7.0,
            'matches_in_previous_14_days': 2.0,
            'matches_in_previous_21_days': 3.0,
            'fixture_congestion': 0.0,
            'pos_DEF': 1.0 if player.element_type == "DEF" else 0.0,
            'pos_MID': 1.0 if player.element_type == "MID" else 0.0,
            'pos_FWD': 1.0 if player.element_type == "FWD" else 0.0
        }
        
        mins_pred = engine.minutes_predictor.predict(pdata)
        
        # Raw ML prediction before shrinkage in minutes_predictor
        if engine.minutes_predictor.is_loaded:
            import pandas as pd
            import numpy as np
            feat_dict = {}
            for col in engine.minutes_predictor.m_mins.feature_name_:
                feat_dict[col] = [float(pdata.get(col, 0.0))]
            df_feat = pd.DataFrame(feat_dict)
            raw_p_start = float(np.clip(engine.minutes_predictor.m_start.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))
            raw_mins = float(np.clip(engine.minutes_predictor.m_mins.predict(df_feat)[0], 0.0, 90.0))
            raw_p_60 = float(np.clip(engine.minutes_predictor.m_60.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))
            raw_p_0 = float(np.clip(engine.minutes_predictor.m_0.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))
        else:
            raw_p_start = raw_mins = raw_p_60 = raw_p_0 = 0.0

        results[name] = {
            "player_id": player.id,
            "web_name": player.web_name,
            "team": player.team.name,
            "element_type": player.element_type,
            "price": player.now_cost / 10.0,
            "ownership": player.selected_by_percent,
            "db_minutes": player.minutes,
            "db_goals": player.goals_scored,
            "db_assists": player.assists,
            "db_expected_goals": player.expected_goals,
            "db_expected_assists": player.expected_assists,
            "breakdown": breakdown,
            "metrics": metrics,
            "raw_mins_ml": raw_mins,
            "raw_p_start": raw_p_start,
            "raw_p_60": raw_p_60,
            "raw_p_0": raw_p_0,
            "calibrated_mins": mins_pred["expected_minutes"],
            "calibrated_p_start": mins_pred["p_start"],
            "calibrated_p_60": mins_pred["p_60_plus"],
            "calibrated_p_zero": mins_pred["p_zero"]
        }
        
    with open("scratch/phase3c6_audit_output.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("Audit data dumped to scratch/phase3c6_audit_output.json")

if __name__ == "__main__":
    run_audit()
