import logging
from typing import Dict, Tuple
from sqlalchemy.orm import Session

from backend.models import Team, Player

logger = logging.getLogger("team_ratings")
logging.basicConfig(level=logging.INFO)

LEAGUE_AVG_RATING = 1000.0
MIN_RATING_BOUND = 600.0
MAX_RATING_BOUND = 1600.0

class TeamRatingCalculator:
    """
    Calculates deterministic team attack and defence ratings based on xG/xGA metrics.
    
    DOCUMENTED CONVENTION:
    - Attacking Rating: Higher = Stronger Attack (scores more xG).
    - Defensive Rating: Higher = BETTER Defence (concedes lower xGA, harder to score against).
    - Baseline League Average = 1000.0.
    """
    def __init__(self, db: Session):
        self.db = db

    def calculate_and_update_team_ratings(self) -> Dict[int, Dict[str, float]]:
        teams = self.db.query(Team).all()
        players = self.db.query(Player).all()

        # Aggregate team xG, xGA, and total minutes
        team_xg = {t.id: 0.0 for t in teams}
        team_xga = {t.id: 0.0 for t in teams}
        team_mins = {t.id: 0 for t in teams}

        for p in players:
            if p.team_id in team_xg:
                team_xg[p.team_id] += (p.expected_goals or 0.0)
                team_xga[p.team_id] += (p.expected_goals_conceded or 0.0)
                team_mins[p.team_id] += (p.minutes or 0)

        # Calculate per-match xG and xGA
        team_games = {}
        team_xg_per_game = {}
        team_xga_per_game = {}

        total_league_xg = 0.0
        total_league_xga = 0.0
        total_league_games = 0

        for t_id, mins in team_mins.items():
            # Roughly 11 players * 90 mins = 990 player-mins per match
            games = max(0.0, mins / 990.0)
            team_games[t_id] = games
            if games >= 1.0:
                xg_pg = team_xg[t_id] / games
                xga_pg = (team_xga[t_id] / 11.0) / games  # xGA is logged per player, so divide by 11
                team_xg_per_game[t_id] = xg_pg
                team_xga_per_game[t_id] = xga_pg
                total_league_xg += xg_pg
                total_league_xga += xga_pg
                total_league_games += 1

        avg_league_xg = (total_league_xg / total_league_games) if total_league_games > 0 else 1.35
        avg_league_xga = (total_league_xga / total_league_games) if total_league_games > 0 else 1.35

        ratings_map = {}

        for t in teams:
            t_id = t.id
            games = team_games.get(t_id, 0.0)

            # Check if official FPL API strength ratings exist (e.g. 1000 - 1350)
            fpl_att_h = float(t.strength_attack_home) if t.strength_attack_home and t.strength_attack_home > 0 else 0.0
            fpl_att_a = float(t.strength_attack_away) if t.strength_attack_away and t.strength_attack_away > 0 else 0.0
            fpl_def_h = float(t.strength_defence_home) if t.strength_defence_home and t.strength_defence_home > 0 else 0.0
            fpl_def_a = float(t.strength_defence_away) if t.strength_defence_away and t.strength_defence_away > 0 else 0.0

            if fpl_att_h > 0 and fpl_att_a > 0 and fpl_def_h > 0 and fpl_def_a > 0:
                att_h = fpl_att_h
                att_a = fpl_att_a
                def_h = fpl_def_h
                def_a = fpl_def_a
            elif games >= 2.0 and t_id in team_xg_per_game:
                obs_att = LEAGUE_AVG_RATING * (team_xg_per_game[t_id] / max(0.5, avg_league_xg))
                # CONVENTION: Higher Def Rating = BETTER Defence (lower xGA)
                obs_def = LEAGUE_AVG_RATING * (max(0.5, avg_league_xga) / max(0.3, team_xga_per_game[t_id]))

                # Bayesian shrinkage toward 1000.0 based on sample size
                w = games / (games + 5.0)
                base_att = (w * obs_att) + ((1.0 - w) * LEAGUE_AVG_RATING)
                base_def = (w * obs_def) + ((1.0 - w) * LEAGUE_AVG_RATING)

                # Home/Away adjustments (+5% Home / -5% Away)
                att_h = base_att * 1.05
                att_a = base_att * 0.95
                def_h = base_def * 1.05
                def_a = base_def * 0.95
            else:
                # Default baseline strength for newly added teams with low data
                att_h = LEAGUE_AVG_RATING * 1.05
                att_a = LEAGUE_AVG_RATING * 0.95
                def_h = LEAGUE_AVG_RATING * 1.05
                def_a = LEAGUE_AVG_RATING * 0.95

            # Apply sensible clamping bounds [600.0, 1600.0]
            att_h = round(min(MAX_RATING_BOUND, max(MIN_RATING_BOUND, att_h)), 1)
            att_a = round(min(MAX_RATING_BOUND, max(MIN_RATING_BOUND, att_a)), 1)
            def_h = round(min(MAX_RATING_BOUND, max(MIN_RATING_BOUND, def_h)), 1)
            def_a = round(min(MAX_RATING_BOUND, max(MIN_RATING_BOUND, def_a)), 1)

            t.strength_attack_home = att_h
            t.strength_attack_away = att_a
            t.strength_defence_home = def_h
            t.strength_defence_away = def_a

            ratings_map[t_id] = {
                "short_name": t.short_name,
                "att_h": att_h, "att_a": att_a,
                "def_h": def_h, "def_a": def_a
            }

        self.db.commit()
        logger.info(f"Updated team ratings for {len(teams)} teams.")
        return ratings_map
