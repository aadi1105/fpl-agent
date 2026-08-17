import logging
import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from backend.config import settings
from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection, ElementType
from backend.projections.team_ratings import TeamRatingCalculator

logger = logging.getLogger("projection_engine")
logging.basicConfig(level=logging.INFO)

PRICE_TIER_DEFAULTS = {
    ElementType.GKP.value: {
        "xg90": 0.0, "xa90": 0.0, "saves90": 3.2, "bps90": 14.0, "cbit90": 0.0
    },
    ElementType.DEF.value: {
        "high": {"xg90": 0.08, "xa90": 0.15, "bps90": 20.0, "cbit90": 6.5},  # > £6.0m
        "mid":  {"xg90": 0.05, "xa90": 0.08, "bps90": 16.0, "cbit90": 7.0},  # £5.0m - £5.5m
        "low":  {"xg90": 0.02, "xa90": 0.03, "bps90": 12.0, "cbit90": 6.0}   # < £5.0m
    },
    ElementType.MID.value: {
        "high": {"xg90": 0.42, "xa90": 0.32, "bps90": 24.0, "cbit90": 3.5},  # > £9.0m
        "mid":  {"xg90": 0.25, "xa90": 0.20, "bps90": 18.0, "cbit90": 4.0},  # £6.5m - £8.5m
        "low":  {"xg90": 0.12, "xa90": 0.10, "bps90": 14.0, "cbit90": 4.5}   # < £6.5m
    },
    ElementType.FWD.value: {
        "high": {"xg90": 0.65, "xa90": 0.22, "bps90": 26.0, "cbit90": 1.5},  # > £9.0m
        "mid":  {"xg90": 0.38, "xa90": 0.15, "bps90": 18.0, "cbit90": 2.0},  # £6.5m - £8.5m
        "low":  {"xg90": 0.22, "xa90": 0.08, "bps90": 14.0, "cbit90": 2.5}   # < £6.5m
    }
}

class ProjectionEngine:
    def __init__(self, db: Session):
        self.db = db

    def calculate_expected_minutes(self, player: Player) -> float:
        """Calculate expected minutes based on injury status, chance of playing, and price tier."""
        if player.status in ["i", "u", "s"]:
            return 0.0
            
        chance = player.chance_of_playing_next_round
        chance_factor = 1.0 if chance is None else (chance / 100.0)
        
        if player.status == "d" and chance is None:
            chance_factor = 0.5

        cost = player.now_cost
        if player.minutes >= 180:
            estimated_games = max(1.0, player.minutes / 75.0)
            avg_mins = min(90.0, max(30.0, player.minutes / estimated_games))
        else:
            if cost >= 90:
                avg_mins = 84.0
            elif cost >= 70:
                avg_mins = 75.0
            elif cost >= 55:
                avg_mins = 65.0
            elif cost >= 45:
                avg_mins = 55.0
            else:
                avg_mins = 35.0

        expected_mins = avg_mins * chance_factor
        return round(min(90.0, max(0.0, expected_mins)), 1)

    def calculate_defcon_probability(self, cbit_match: float) -> float:
        """
        Calculate exact probability of a defender reaching 10+ CBIT in a match.
        Uses Poisson cumulative probability model: P(X >= 10 | lambda = cbit_match)
        """
        if cbit_match <= 0.0:
            return 0.0
            
        prob_under_10 = 0.0
        for k in range(10):
            prob_under_10 += (math.pow(cbit_match, k) * math.exp(-cbit_match)) / math.factorial(k)

        prob_10_plus = 1.0 - prob_under_10
        return round(min(0.85, max(0.0, prob_10_plus)), 3)

    def get_player_per_90_metrics(self, player: Player) -> Dict[str, float]:
        """Extract or derive per-90 underlying metrics."""
        pos = player.element_type
        cost = player.now_cost

        if cost >= 90 if pos in ["MID", "FWD"] else cost >= 60:
            tier = "high"
        elif cost >= 65 if pos in ["MID", "FWD"] else cost >= 50:
            tier = "mid"
        else:
            tier = "low"

        defaults = PRICE_TIER_DEFAULTS.get(pos, {})
        if pos != ElementType.GKP.value:
            defaults = defaults.get(tier, {})

        if player.minutes >= 180:
            m_factor = 90.0 / player.minutes
            xg90 = max(0.0, player.expected_goals * m_factor)
            xa90 = max(0.0, player.expected_assists * m_factor)
            bps90 = max(0.0, player.bps * m_factor)
            cbit90 = max(0.0, player.defensive_contributions * m_factor)
            saves90 = max(0.0, player.saves * m_factor) if pos == ElementType.GKP.value else 0.0
        else:
            xg90 = defaults.get("xg90", 0.05)
            xa90 = defaults.get("xa90", 0.05)
            bps90 = defaults.get("bps90", 15.0)
            cbit90 = defaults.get("cbit90", 5.0)
            saves90 = defaults.get("saves90", 3.0) if pos == ElementType.GKP.value else 0.0

        return {
            "xg90": xg90,
            "xa90": xa90,
            "bps90": bps90,
            "cbit90": cbit90,
            "saves90": saves90
        }

    def calculate_player_xp_breakdown(
        self, 
        player: Player, 
        fixture: Optional[Fixture], 
        is_home: bool,
        opponent_team: Optional[Team]
    ) -> Dict[str, Any]:
        """
        Calculates fixture-specific expected points breakdown using Team Strength Ratings.
        
        CONVENTIONS:
        - Attacking Rating: Higher = Stronger Attack (scores more xG).
        - Defensive Rating: Higher = BETTER Defence (concedes lower xGA, harder to score against).
        - League Average = 1000.0.
        """
        x_mins = self.calculate_expected_minutes(player)
        mins_ratio = x_mins / 90.0
        
        pos = player.element_type
        metrics = self.get_player_per_90_metrics(player)
        team = player.team

        # Extract ratings with 1000.0 baseline fallback
        if opponent_team:
            raw_opp_def = opponent_team.strength_defence_away if is_home else opponent_team.strength_defence_home
            opp_def_rating = float(raw_opp_def) if raw_opp_def and raw_opp_def > 0 else 1000.0
            
            raw_opp_att = opponent_team.strength_attack_away if is_home else opponent_team.strength_attack_home
            opp_att_rating = float(raw_opp_att) if raw_opp_att and raw_opp_att > 0 else 1000.0
            opp_short_name = opponent_team.short_name
        else:
            opp_def_rating = 1000.0
            opp_att_rating = 1000.0
            opp_short_name = "BYE"

        if team:
            raw_team_att = team.strength_attack_home if is_home else team.strength_attack_away
            team_att_rating = float(raw_team_att) if raw_team_att and raw_team_att > 0 else 1000.0

            raw_team_def = team.strength_defence_home if is_home else team.strength_defence_away
            team_def_rating = float(raw_team_def) if raw_team_def and raw_team_def > 0 else 1000.0
        else:
            team_att_rating = 1000.0
            team_def_rating = 1000.0

        ha_att_factor = 1.05 if is_home else 0.95
        ha_def_factor = 1.05 if is_home else 0.95

        # 1. Single Fixture Attacking Multiplier (Clamped between 0.60 and 1.50)
        raw_att_mult = (1000.0 / max(400.0, opp_def_rating)) * ha_att_factor
        att_multiplier = min(1.50, max(0.60, raw_att_mult))

        # 2. Defensive Ratio for Clean Sheets (Clamped between 0.40 and 2.50)
        raw_cs_ratio = (team_def_rating / max(400.0, opp_att_rating)) * ha_def_factor
        cs_ratio = min(2.50, max(0.40, raw_cs_ratio))
        cs_prob = round(min(0.75, max(0.04, 0.32 * cs_ratio)), 3)

        if mins_ratio == 0.0:
            return {
                "web_name": player.web_name,
                "position": pos,
                "price": player.now_cost / 10.0,
                "price_str": f"£{player.now_cost / 10.0:.1f}m",
                "opponent": f"{opp_short_name} ({'H' if is_home else 'A'})",
                "is_home": is_home,
                "opp_short_name": opp_short_name,
                "fixture_difficulty": (fixture.team_a_difficulty if is_home else fixture.team_h_difficulty) if fixture else 3,
                "team_attack_rating": round(team_att_rating, 1),
                "team_defence_rating": round(team_def_rating, 1),
                "opp_attack_rating": round(opp_att_rating, 1),
                "opp_defence_rating": round(opp_def_rating, 1),
                "fixture_attack_modifier": round(att_multiplier, 3),
                "fixture_defence_modifier": round(cs_ratio, 3),
                "xMins": 0.0, "total_xp": 0.0,
                "appearance_xp": 0.0, "goals_xp": 0.0, "assists_xp": 0.0,
                "cs_xp": 0.0, "defcon_xp": 0.0, "bonus_xp": 0.0,
                "saves_xp": 0.0, "cards_xp": 0.0, "xp_per_m": 0.0
            }

        # 3. Appearance Points
        appearance_xp = (2.0 if x_mins >= 60 else 1.0) * mins_ratio

        # 4. Goals & Assists Points
        xg_match = metrics["xg90"] * mins_ratio * att_multiplier
        xa_match = metrics["xa90"] * mins_ratio * att_multiplier

        goal_val = 6.0 if pos in [ElementType.DEF.value, ElementType.GKP.value] else (5.0 if pos == ElementType.MID.value else 4.0)
        assist_val = 3.0

        goals_xp = xg_match * goal_val
        assists_xp = xa_match * assist_val

        # 5. Clean Sheet Points
        if pos in [ElementType.GKP.value, ElementType.DEF.value]:
            cs_xp = cs_prob * 4.0 * mins_ratio
        elif pos == ElementType.MID.value:
            cs_xp = cs_prob * 1.0 * mins_ratio
        else:
            cs_xp = 0.0

        # 6. DEFCON (CBIT) Probability for Defenders (Scaled by Opponent Attacking Strength)
        defcon_xp = 0.0
        defcon_prob = 0.0
        if pos == ElementType.DEF.value:
            cbit_multiplier = min(1.80, max(0.50, opp_att_rating / 1000.0))
            cbit_match = metrics["cbit90"] * mins_ratio * cbit_multiplier
            defcon_prob = self.calculate_defcon_probability(cbit_match)
            defcon_xp = defcon_prob * settings.DEFCON_POINTS * mins_ratio

        # 7. Saves Points (GKP)
        saves_xp = 0.0
        if pos == ElementType.GKP.value:
            save_multiplier = min(1.80, max(0.50, opp_att_rating / 1000.0))
            saves_match = metrics["saves90"] * mins_ratio * save_multiplier
            saves_xp = (saves_match / 3.0) * 1.0

        # 8. Bonus Points
        bonus_prob = max(0.0, (metrics["bps90"] - 14.0) / 22.0)
        bonus_xp = min(1.2, bonus_prob) * mins_ratio

        # 9. Card / Penalty Risk
        cards_xp = -0.10 * mins_ratio

        raw_total = appearance_xp + goals_xp + assists_xp + cs_xp + defcon_xp + saves_xp + bonus_xp + cards_xp
        total_xp = max(0.0, round(raw_total, 2))

        diff = (fixture.team_a_difficulty if is_home else fixture.team_h_difficulty) if fixture else 3

        return {
            "web_name": player.web_name,
            "position": pos,
            "price": player.now_cost / 10.0,
            "price_str": f"£{player.now_cost / 10.0:.1f}m",
            "opponent": f"{opp_short_name} ({'H' if is_home else 'A'})",
            "is_home": is_home,
            "opp_short_name": opp_short_name,
            "fixture_difficulty": diff,
            "team_attack_rating": round(team_att_rating, 1),
            "team_defence_rating": round(team_def_rating, 1),
            "opp_attack_rating": round(opp_att_rating, 1),
            "opp_defence_rating": round(opp_def_rating, 1),
            "fixture_attack_modifier": round(att_multiplier, 3),
            "fixture_defence_modifier": round(cs_ratio, 3),
            "xMins": x_mins,
            "xg_match": round(xg_match, 3),
            "xa_match": round(xa_match, 3),
            "cs_prob": cs_prob,
            "defcon_prob": defcon_prob,
            "appearance_xp": round(appearance_xp, 2),
            "goals_xp": round(goals_xp, 2),
            "assists_xp": round(assists_xp, 2),
            "cs_xp": round(cs_xp, 2),
            "defcon_xp": round(defcon_xp, 2),
            "saves_xp": round(saves_xp, 2),
            "bonus_xp": round(bonus_xp, 2),
            "cards_xp": round(cards_xp, 2),
            "total_xp": total_xp,
            "xp_per_m": round(total_xp / max(4.0, player.now_cost / 10.0), 2)
        }

    def run_projections(self, start_gw: int = 1, end_gw: int = 8, source: str = "internal") -> int:
        """Generate and store fixture-specific base projections for all players across specified gameweeks."""
        logger.info(f"Updating team ratings before running projections...")
        rating_calc = TeamRatingCalculator(self.db)
        rating_calc.calculate_and_update_team_ratings()

        logger.info(f"Running team-strength fixture projection engine for GW{start_gw} to GW{end_gw} (Source: {source})")
        players = self.db.query(Player).all()
        teams_map = {t.id: t for t in self.db.query(Team).all()}
        
        saved_count = 0

        for gw_id in range(start_gw, end_gw + 1):
            fixtures = self.db.query(Fixture).filter(Fixture.event_id == gw_id).all()
            
            team_fixture_map: Dict[int, List[tuple]] = {}
            for f in fixtures:
                if f.team_h_id not in team_fixture_map:
                    team_fixture_map[f.team_h_id] = []
                team_fixture_map[f.team_h_id].append((f, True, teams_map.get(f.team_a_id)))

                if f.team_a_id not in team_fixture_map:
                    team_fixture_map[f.team_a_id] = []
                team_fixture_map[f.team_a_id].append((f, False, teams_map.get(f.team_h_id)))

            for player in players:
                player_fixtures = team_fixture_map.get(player.team_id, [])
                
                if not player_fixtures:
                    total_xMins = 0.0
                    total_xP = 0.0
                else:
                    total_xMins = 0.0
                    total_xP = 0.0
                    for f, is_home, opp_team in player_fixtures:
                        res = self.calculate_player_xp_breakdown(player, f, is_home, opp_team)
                        total_xMins += res["xMins"]
                        total_xP += res["total_xp"]

                proj = self.db.query(PlayerProjection).filter(
                    PlayerProjection.player_id == player.id,
                    PlayerProjection.gameweek_id == gw_id,
                    PlayerProjection.source == source
                ).first()

                if not proj:
                    proj = PlayerProjection(
                        player_id=player.id,
                        gameweek_id=gw_id,
                        source=source
                    )
                    self.db.add(proj)

                proj.expected_minutes = round(total_xMins, 1)
                proj.expected_points = round(total_xP, 2)
                proj.updated_at = datetime.utcnow()
                saved_count += 1

        self.db.commit()
        logger.info(f"Successfully updated {saved_count} projection records across GW{start_gw}-{end_gw}.")
        return saved_count
