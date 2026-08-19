import os
import pickle
import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger("cs_predictor")

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "cs_v1_lgbm.pkl")
MODEL_VERSION = "cs_v1_lgbm"
FALLBACK_VERSION = "cs_baseline_v1"

class CSPredictor:
    """Predictor wrapper for Clean Sheet Probability LightGBM Model."""
    def __init__(self):
        self.model = None
        self.version = MODEL_VERSION
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                logger.info(f"Successfully loaded Clean Sheet ML model from {MODEL_PATH}")
            except Exception as e:
                logger.error(f"Failed to load Clean Sheet ML model: {e}", exc_info=True)
                self.model = None
        else:
            logger.warning(f"Clean Sheet ML model not found at {MODEL_PATH}. Using fallback baseline.")

    def get_fallback_prediction(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        is_home = float(pdata.get("is_home", 1.0 if pdata.get("home_away_is_home", 1.0) == 1.0 else 0.0))
        diff = float(pdata.get("fixture_difficulty", 3.0))
        team_def = float(pdata.get("team_defence_rating", 1000.0))
        opp_att = float(pdata.get("opponent_attack_rating", 1000.0))

        home_factor = 1.05 if is_home == 1.0 else 0.95
        cs_ratio = min(2.50, max(0.40, (team_def / max(1.0, opp_att)) * home_factor))
        cs_prob = round(min(0.75, max(0.04, 0.32 * cs_ratio)), 3)

        return {
            "clean_sheet_probability": cs_prob,
            "model_version": FALLBACK_VERSION,
            "used_fallback": True
        }

    def predict(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        if not self.model:
            return self.get_fallback_prediction(pdata)

        try:
            is_home = float(pdata.get("is_home", 1.0 if pdata.get("home_away_is_home", 1.0) == 1.0 else 0.0))
            team_cs_rate_last_5 = float(pdata.get("team_cs_rate_last_5", 0.30))
            team_gc_avg_last_5 = float(pdata.get("team_gc_avg_last_5", 1.20))
            team_def = float(pdata.get("team_defence_rating", 1000.0))
            opp_att = float(pdata.get("opponent_attack_rating", 1000.0))

            cs_modifier = min(1.80, max(0.50, team_def / max(1.0, opp_att)))

            features = pd.DataFrame([{
                'is_home': is_home,
                'team_cs_rate_last_5': team_cs_rate_last_5,
                'team_gc_avg_last_5': team_gc_avg_last_5
            }])

            base_prob = float(self.model.predict_proba(features)[0, 1])
            adjusted_prob = base_prob * cs_modifier
            prob_clamped = round(min(0.85, max(0.04, adjusted_prob)), 3)

            return {
                "clean_sheet_probability": prob_clamped,
                "model_version": MODEL_VERSION,
                "used_fallback": False
            }
        except Exception as e:
            logger.error(f"Clean Sheet ML prediction error: {e}", exc_info=True)
            return self.get_fallback_prediction(pdata)
