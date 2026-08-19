import logging
import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from backend.config import settings
from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection, ElementType
from backend.projections.team_ratings import TeamRatingCalculator
from backend.ml.minutes_predictor import MinutesPredictor
from backend.ml.xg_predictor import XGPredictor
from backend.ml.xa_predictor import XAPredictor
from backend.ml.cs_predictor import CSPredictor
from backend.ml.defcon_predictor import DEFCONPredictor

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
    def __init__(
        self,
        db: Session,
        use_ml_minutes: bool = True,
        use_ml_xg: bool = True,
        use_ml_xa: bool = True,
        use_ml_cs: bool = True,
        use_ml_defcon: bool = True
    ):
        self.db = db
        self.use_ml_minutes = use_ml_minutes
        self.use_ml_xg = use_ml_xg
        self.use_ml_xa = use_ml_xa
        self.use_ml_cs = use_ml_cs
        self.use_ml_defcon = use_ml_defcon
        self.minutes_predictor = MinutesPredictor()
        self.xg_predictor = XGPredictor()
        self.xa_predictor = XAPredictor()
        self.cs_predictor = CSPredictor()
        self.defcon_predictor = DEFCONPredictor()

    def calculate_expected_minutes(self, player: Player) -> float:
        """Calculate deterministic baseline expected minutes."""
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
        """Poisson probability model for 2026/27 DEFCON rules."""
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
            factor = 90.0 / player.minutes
            return {
                "xg90": round(player.expected_goals * factor, 3),
                "xa90": round(player.expected_assists * factor, 3),
                "saves90": round(defaults.get("saves90", 0.0), 2),
                "bps90": round(player.bps * factor, 2),
                "cbit90": round(defaults.get("cbit90", 4.0), 2)
            }
        else:
            return {
                "xg90": defaults.get("xg90", 0.05),
                "xa90": defaults.get("xa90", 0.05),
                "saves90": defaults.get("saves90", 0.0),
                "bps90": defaults.get("bps90", 15.0),
                "cbit90": defaults.get("cbit90", 4.0)
            }

    def calculate_player_xp_breakdown(
        self,
        player: Player,
        fixture: Optional[Fixture] = None,
        is_home: bool = True,
        opp_team: Optional[Team] = None
    ) -> Dict[str, Any]:
        """Calculate complete component breakdown for a player in a specific fixture."""
        pos = player.element_type
        metrics = self.get_player_per_90_metrics(player)
        diff = (fixture.team_a_difficulty if is_home else fixture.team_h_difficulty) if fixture else 3

        # Deterministic Baseline Minutes
        baseline_xMins = self.calculate_expected_minutes(player)

        # Team Strength Ratings
        player_team = player.team
        raw_team_att = (player_team.strength_attack_home if is_home else player_team.strength_attack_away) if player_team else 1000.0
        team_att_rating = raw_team_att if raw_team_att > 0 else 1000.0

        raw_team_def = (player_team.strength_defence_home if is_home else player_team.strength_defence_away) if player_team else 1000.0
        team_def_rating = raw_team_def if raw_team_def > 0 else 1000.0

        raw_opp_att = (opp_team.strength_attack_away if is_home else opp_team.strength_attack_home) if opp_team else 1000.0
        opp_att_rating = raw_opp_att if raw_opp_att > 0 else 1000.0

        raw_opp_def = (opp_team.strength_defence_away if is_home else opp_team.strength_defence_home) if opp_team else 1000.0
        opp_def_rating = raw_opp_def if raw_opp_def > 0 else 1000.0

        home_factor = 1.05 if is_home else 0.95
        att_multiplier = min(1.50, max(0.60, (1000.0 / opp_def_rating) * home_factor))
        cs_ratio = min(2.50, max(0.40, (team_def_rating / opp_att_rating) * home_factor))
        cs_prob = round(min(0.75, max(0.04, 0.32 * cs_ratio)), 3)
        opp_short_name = opp_team.short_name if opp_team else "OPP"

        # ML Minutes Prediction (with safe fallback)
        tot_mins = float(player.minutes)
        recent_mins_5 = float(min(450.0, tot_mins))
        recent_apps_5 = float(min(5.0, tot_mins / 60.0)) if tot_mins > 0 else 0.0
        recent_starts_5 = float(min(5.0, tot_mins / 80.0)) if tot_mins >= 80 else 0.0
        avg_mins_5 = float(recent_mins_5 / max(1.0, recent_apps_5)) if recent_apps_5 > 0 else 0.0

        pdata = {
            'price': player.now_cost / 10.0,
            'fixture_difficulty': diff,
            'team_attack_rating': team_att_rating,
            'team_defence_rating': team_def_rating,
            'opponent_attack_rating': opp_att_rating,
            'opponent_defence_rating': opp_def_rating,
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
            'pos_DEF': 1.0 if pos == "DEF" else 0.0,
            'pos_MID': 1.0 if pos == "MID" else 0.0,
            'pos_FWD': 1.0 if pos == "FWD" else 0.0
        }

        ml_pred = self.minutes_predictor.predict(pdata)
        
        # Decide active xMins (ML if enabled and valid, else baseline)
        if self.use_ml_minutes and not ml_pred["used_fallback"]:
            x_mins = ml_pred["expected_minutes"]
        else:
            x_mins = baseline_xMins

        mins_ratio = min(1.0, max(0.0, x_mins / 90.0))

        if x_mins <= 0.0:
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
                "expected_minutes_baseline": baseline_xMins,
                "expected_minutes_ml": ml_pred["expected_minutes"],
                "model_version": ml_pred["model_version"],
                "p_start": ml_pred["p_start"],
                "p_60_plus": ml_pred["p_60_plus"],
                "p_zero": ml_pred["p_zero"],
                "used_fallback": ml_pred["used_fallback"],
                "xMins": 0.0,
                "xg_match": 0.0,
                "xa_match": 0.0,
                "cs_prob": cs_prob,
                "defcon_prob": 0.0,
                "appearance_xp": 0.0,
                "goals_xp": 0.0,
                "assists_xp": 0.0,
                "cs_xp": 0.0,
                "defcon_xp": 0.0,
                "saves_xp": 0.0,
                "bonus_xp": 0.0,
                "cards_xp": 0.0,
                "total_xp": 0.0,
                "xp_per_m": 0.0
            }

        # Appearance Points
        appearance_xp = (2.0 if x_mins >= 60 else 1.0) * mins_ratio

        # Deterministic Baseline xG
        baseline_xg = metrics["xg90"] * mins_ratio * att_multiplier

        # Construct properly-scaled rolling features for xG predictor
        est_games = max(1.0, player.minutes / 75.0) if player.minutes >= 180 else 1.0
        g_cnt = player.goals_scored if (player.goals_scored and player.goals_scored > 0) else getattr(player, 'expected_goals', 0.0)
        a_cnt = player.assists if (player.assists and player.assists > 0) else getattr(player, 'expected_assists', 0.0)
        g_per_game = float(g_cnt) / est_games
        a_per_game = float(a_cnt) / est_games

        xg_pdata = {
            "price": player.now_cost / 10.0,
            "fixture_difficulty": diff,
            "team_attack_rating": team_att_rating,
            "team_defence_rating": team_def_rating,
            "opponent_attack_rating": opp_att_rating,
            "opponent_defence_rating": opp_def_rating,
            "expected_minutes_v1": x_mins,
            "p_start": ml_pred["p_start"],
            "p_60_plus": ml_pred["p_60_plus"],
            "p_zero": ml_pred["p_zero"],
            "minutes_last_1": float(min(90.0, player.minutes / est_games)),
            "minutes_last_5": float(min(450.0, (player.minutes / est_games) * 5.0)),
            "starts_last_5": float(min(5.0, 5.0 if player.minutes >= 180 else 1.0)),
            "goals_last_1": float(min(2.0, g_per_game)),
            "goals_last_3": float(min(6.0, g_per_game * 3.0)),
            "goals_last_5": float(min(10.0, g_per_game * 5.0)),
            "goals_last_10": float(min(20.0, g_per_game * 10.0)),
            "xg_last_1": float(min(2.0, g_per_game * 0.85)),
            "xg_last_3": float(min(6.0, g_per_game * 0.85 * 3.0)),
            "xg_last_5": float(min(10.0, g_per_game * 0.85 * 5.0)),
            "xg_last_10": float(min(20.0, g_per_game * 0.85 * 10.0)),
            "threat_last_5": float(min(500.0, g_per_game * 60.0 * 5.0)),
            "threat_last_10": float(min(1000.0, g_per_game * 60.0 * 10.0)),
            "creativity_last_5": float(min(500.0, a_per_game * 40.0 * 5.0)),
            "goals_per_90_last_5": float(min(2.0, (g_per_game / max(30.0, player.minutes / est_games)) * 90.0)),
            "xg_per_90_last_5": float(min(2.0, (g_per_game * 0.85 / max(30.0, player.minutes / est_games)) * 90.0)),
            "threat_per_90_last_5": float(min(100.0, (g_per_game * 60.0 / max(30.0, player.minutes / est_games)) * 90.0)),
            "position": pos,
            "home_away_is_home": 1.0 if is_home else 0.0
        }

        xg_pred = self.xg_predictor.predict(xg_pdata)
        if self.use_ml_xg and not xg_pred["used_fallback"]:
            xg_match = xg_pred["expected_goals"] * att_multiplier
        else:
            xg_match = baseline_xg
            
        # Deterministic Baseline xA
        baseline_xa = metrics["xa90"] * mins_ratio * att_multiplier

        # ML xA Prediction
        xa_pdata = {
            "price": player.now_cost / 10.0,
            "fixture_difficulty": diff,
            "team_attack_rating": team_att_rating,
            "team_defence_rating": team_def_rating,
            "opponent_attack_rating": opp_att_rating,
            "opponent_defence_rating": opp_def_rating,
            "expected_minutes_v1": x_mins,
            "p_start": ml_pred["p_start"],
            "p_60_plus": ml_pred["p_60_plus"],
            "p_zero": ml_pred["p_zero"],
            "minutes_last_1": float(min(90.0, player.minutes / est_games)),
            "minutes_last_5": float(min(450.0, (player.minutes / est_games) * 5.0)),
            "starts_last_5": float(min(5.0, 5.0 if player.minutes >= 180 else 1.0)),
            "assists_last_1": float(min(2.0, a_per_game)),
            "assists_last_3": float(min(6.0, a_per_game * 3.0)),
            "assists_last_5": float(min(10.0, a_per_game * 5.0)),
            "assists_last_10": float(min(20.0, a_per_game * 10.0)),
            "xa_last_1": float(min(2.0, a_per_game * 0.75)),
            "xa_last_3": float(min(6.0, a_per_game * 0.75 * 3.0)),
            "xa_last_5": float(min(10.0, a_per_game * 0.75 * 5.0)),
            "xa_last_10": float(min(20.0, a_per_game * 0.75 * 10.0)),
            "creativity_last_5": float(min(500.0, a_per_game * 40.0 * 5.0)),
            "creativity_last_10": float(min(1000.0, a_per_game * 40.0 * 10.0)),
            "threat_last_5": float(min(500.0, g_per_game * 60.0 * 5.0)),
            "assists_per_90_last_5": float(min(2.0, (a_per_game / max(30.0, player.minutes / est_games)) * 90.0)),
            "xa_per_90_last_5": float(min(2.0, (a_per_game * 0.75 / max(30.0, player.minutes / est_games)) * 90.0)),
            "creativity_per_90_last_5": float(min(100.0, (a_per_game * 40.0 / max(30.0, player.minutes / est_games)) * 90.0)),
            "position": pos,
            "home_away_is_home": 1.0 if is_home else 0.0,
            "xg_v1_lgbm_pred": xg_pred["expected_goals"]
        }

        xa_pred = self.xa_predictor.predict(xa_pdata)
        if self.use_ml_xa and not xa_pred["used_fallback"]:
            xa_match = xa_pred["expected_assists"] * att_multiplier
        else:
            xa_match = baseline_xa

        # ML Clean Sheet Prediction
        cs_pdata = {
            "is_home": 1.0 if is_home else 0.0,
            "fixture_difficulty": diff,
            "team_defence_rating": team_def_rating,
            "opponent_attack_rating": opp_att_rating,
            "team_cs_last_5": 1.5,
            "team_gc_avg_last_5": 1.2,
            "opp_goals_last_5": 1.3
        }
        cs_pred = self.cs_predictor.predict(cs_pdata)
        cs_prob = cs_pred["clean_sheet_probability"]

        # ML / Poisson DEFCON Prediction (2026/27 Rules)
        defcon_pdata = {
            "position": pos,
            "expected_minutes_v1": x_mins,
            "cbit90": metrics.get("cbit90", 4.0),
            "opponent_attack_rating": opp_att_rating
        }
        defcon_pred = self.defcon_predictor.predict(defcon_pdata)
        defcon_prob = defcon_pred["defcon_probability"]

        goal_val = 6.0 if pos in [ElementType.DEF.value, ElementType.GKP.value] else (5.0 if pos == ElementType.MID.value else 4.0)
        assist_val = 3.0

        goals_xp = xg_match * goal_val
        assists_xp = xa_match * assist_val

        # Clean Sheet Points (2026/27 FPL Rules)
        if pos in [ElementType.GKP.value, ElementType.DEF.value]:
            cs_xp = cs_prob * 4.0 * mins_ratio
        elif pos == ElementType.MID.value:
            cs_xp = cs_prob * 1.0 * mins_ratio
        else:
            cs_xp = 0.0

        # DEFCON Points (2026/27 FPL Rules: +2 points capped per match)
        defcon_xp = defcon_prob * settings.DEFCON_POINTS * mins_ratio

        # Saves Points
        saves_xp = 0.0
        if pos == ElementType.GKP.value:
            save_multiplier = min(1.80, max(0.50, opp_att_rating / 1000.0))
            saves_match = metrics["saves90"] * mins_ratio * save_multiplier
            saves_xp = (saves_match / 3.0) * 1.0

        # Bonus Points (2026/27 Baseline BPS Rules)
        bonus_prob = max(0.0, (metrics["bps90"] - 14.0) / 22.0)
        bonus_xp = min(1.2, bonus_prob) * mins_ratio

        # Cards Risk
        cards_xp = -0.10 * mins_ratio

        raw_total = appearance_xp + goals_xp + assists_xp + cs_xp + defcon_xp + saves_xp + bonus_xp + cards_xp
        total_xp = max(0.0, round(raw_total, 2))

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
            "expected_minutes_baseline": baseline_xMins,
            "expected_minutes_ml": ml_pred["expected_minutes"],
            "model_version": ml_pred["model_version"],
            "p_start": ml_pred["p_start"],
            "p_60_plus": ml_pred["p_60_plus"],
            "p_zero": ml_pred["p_zero"],
            "used_fallback": ml_pred["used_fallback"],
            "xg_baseline": round(baseline_xg, 3),
            "xg_ml": round(xg_pred["expected_goals"], 3),
            "xg_model_version": xg_pred["model_version"],
            "used_xg_fallback": xg_pred["used_fallback"],
            "xa_baseline": round(baseline_xa, 3),
            "xa_ml": round(xa_pred["expected_assists"], 3),
            "xa_model_version": xa_pred["model_version"],
            "used_xa_fallback": xa_pred["used_fallback"],
            "cs_model_version": cs_pred["model_version"],
            "used_cs_fallback": cs_pred.get("used_fallback", False),
            "defcon_model_version": defcon_pred["model_version"],
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
