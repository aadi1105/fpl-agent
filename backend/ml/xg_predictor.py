import os
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger("xg_predictor")

MODEL_DIR = "models"
FEATURE_COLS = [
    "price", "fixture_difficulty",
    "team_attack_rating", "team_defence_rating",
    "opponent_attack_rating", "opponent_defence_rating",
    "expected_minutes_v1", "p_start", "p_60_plus", "p_zero",
    "minutes_last_1", "minutes_last_5", "starts_last_5",
    "goals_last_1", "goals_last_3", "goals_last_5", "goals_last_10",
    "xg_last_1", "xg_last_3", "xg_last_5", "xg_last_10",
    "threat_last_5", "threat_last_10", "creativity_last_5",
    "goals_per_90_last_5", "xg_per_90_last_5", "threat_per_90_last_5",
    "pos_GKP", "pos_DEF", "pos_MID", "pos_FWD",
    "home_away_is_home"
]

POSITION_BASELINE_XG90 = {
    "GKP": 0.0,
    "DEF": 0.04,
    "MID": 0.22,
    "FWD": 0.40
}

class XGPredictor:
    """
    Production Inference Wrapper for Expected Goals (xG) ML Models.
    Includes safe automatic fallback to deterministic baseline if models fail.
    """
    def __init__(self, model_dir: str = MODEL_DIR):
        self.model_dir = model_dir
        self.model = None
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        try:
            model_path = os.path.join(self.model_dir, "xg_v1_lgbm.pkl")
            if os.path.exists(model_path):
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
                self.is_loaded = True
                logger.info("Successfully loaded Expected Goals (xG) ML model.")
            else:
                logger.warning(f"xG ML model pickle file missing at {model_path}. Fallback enabled.")
        except Exception as e:
            logger.error(f"Failed to load xG ML model: {e}. Fallback enabled.")
            self.is_loaded = False

    def get_fallback_prediction(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        """Compute deterministic baseline xG prediction as fallback."""
        pos = str(pdata.get("position", "MID"))
        price = float(pdata.get("price", pdata.get("now_cost", 50) / 10.0))
        x_mins = float(pdata.get("expected_minutes_v1", pdata.get("expected_minutes", 60.0)))
        mins_ratio = min(1.0, max(0.0, x_mins / 90.0))
        
        base_xg90 = POSITION_BASELINE_XG90.get(pos, 0.20)
        if pos == "FWD":
            if price >= 9.0: base_xg90 = 0.55
            elif price >= 7.0: base_xg90 = 0.40
            else: base_xg90 = 0.25
        elif pos == "MID":
            if price >= 9.0: base_xg90 = 0.45
            elif price >= 7.0: base_xg90 = 0.30
            else: base_xg90 = 0.15
        elif pos == "DEF":
            if price >= 6.0: base_xg90 = 0.08
            else: base_xg90 = 0.04

        opp_def = float(pdata.get("opponent_defence_rating", 1000.0))
        is_home = bool(pdata.get("home_away_is_home", 1.0 if pdata.get("home_away", "H") == "H" else 0.0))
        home_factor = 1.05 if is_home else 0.95
        att_multiplier = min(1.50, max(0.60, (1000.0 / max(300.0, opp_def)) * home_factor))
        
        baseline_xg = max(0.0, base_xg90 * mins_ratio * att_multiplier)

        return {
            "expected_goals": round(baseline_xg, 3),
            "model_version": "xg_baseline_v1",
            "used_fallback": True
        }

    def predict(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        """Predict fixture-level expected goals (xG) using ML model or fallback."""
        if not self.is_loaded:
            return self.get_fallback_prediction(pdata)

        try:
            pos = str(pdata.get("position", "MID"))
            is_home = bool(pdata.get("home_away_is_home", 1.0 if pdata.get("home_away", "H") == "H" else 0.0))

            feat_dict = {
                "price": [float(pdata.get("price", pdata.get("now_cost", 50) / 10.0))],
                "fixture_difficulty": [float(pdata.get("fixture_difficulty", 3))],
                "team_attack_rating": [float(pdata.get("team_attack_rating", 1000.0))],
                "team_defence_rating": [float(pdata.get("team_defence_rating", 1000.0))],
                "opponent_attack_rating": [float(pdata.get("opponent_attack_rating", 1000.0))],
                "opponent_defence_rating": [float(pdata.get("opponent_defence_rating", 1000.0))],
                "expected_minutes_v1": [float(pdata.get("expected_minutes_v1", pdata.get("expected_minutes", 60.0)))],
                "p_start": [float(pdata.get("p_start", 0.7))],
                "p_60_plus": [float(pdata.get("p_60_plus", 0.6))],
                "p_zero": [float(pdata.get("p_zero", 0.1))],
                "minutes_last_1": [float(pdata.get("minutes_last_1", 60.0))],
                "minutes_last_5": [float(pdata.get("minutes_last_5", 300.0))],
                "starts_last_5": [float(pdata.get("starts_last_5", 3.0))],
                "goals_last_1": [float(pdata.get("goals_last_1", 0.0))],
                "goals_last_3": [float(pdata.get("goals_last_3", 0.0))],
                "goals_last_5": [float(pdata.get("goals_last_5", 0.0))],
                "goals_last_10": [float(pdata.get("goals_last_10", 0.0))],
                "xg_last_1": [float(pdata.get("xg_last_1", 0.0))],
                "xg_last_3": [float(pdata.get("xg_last_3", 0.0))],
                "xg_last_5": [float(pdata.get("xg_last_5", 0.0))],
                "xg_last_10": [float(pdata.get("xg_last_10", 0.0))],
                "threat_last_5": [float(pdata.get("threat_last_5", 20.0))],
                "threat_last_10": [float(pdata.get("threat_last_10", 40.0))],
                "creativity_last_5": [float(pdata.get("creativity_last_5", 20.0))],
                "goals_per_90_last_5": [float(pdata.get("goals_per_90_last_5", 0.0))],
                "xg_per_90_last_5": [float(pdata.get("xg_per_90_last_5", 0.0))],
                "threat_per_90_last_5": [float(pdata.get("threat_per_90_last_5", 6.0))],
                "pos_GKP": [1.0 if pos == "GKP" else 0.0],
                "pos_DEF": [1.0 if pos == "DEF" else 0.0],
                "pos_MID": [1.0 if pos == "MID" else 0.0],
                "pos_FWD": [1.0 if pos == "FWD" else 0.0],
                "home_away_is_home": [1.0 if is_home else 0.0]
            }

            df_feat = pd.DataFrame(feat_dict)
            raw_xg = float(self.model.predict(df_feat)[0])
            exp_xg = float(np.clip(raw_xg, 0.0, 3.5))

            return {
                "expected_goals": round(exp_xg, 3),
                "model_version": "xg_v1_lgbm",
                "used_fallback": False
            }
        except Exception as e:
            logger.error(f"Inference error for xG data: {e}. Utilizing fallback.")
            return self.get_fallback_prediction(pdata)
