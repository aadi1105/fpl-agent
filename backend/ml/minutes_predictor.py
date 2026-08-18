import os
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

logger = logging.getLogger("minutes_predictor")

MODEL_DIR = "models"
FEATURE_COLS = [
    'price', 'fixture_difficulty',
    'team_attack_rating', 'team_defence_rating',
    'opponent_attack_rating', 'opponent_defence_rating',
    'home_away_is_home',
    'minutes_last_1', 'minutes_last_3', 'minutes_last_5', 'minutes_last_10',
    'starts_last_1', 'starts_last_3', 'starts_last_5', 'starts_last_10',
    'appearances_last_5', 'bench_appearances_last_5', 'unused_substitute_last_5',
    'average_minutes_last_5', 'average_minutes_last_10',
    'days_since_last_match', 'matches_in_previous_14_days', 'matches_in_previous_21_days',
    'fixture_congestion',
    'pos_DEF', 'pos_MID', 'pos_FWD'
]

class MinutesPredictor:
    """
    Production Inference Wrapper for Expected Minutes & Availability ML Models.
    Includes safe automatic fallback to deterministic baseline if models fail.
    """
    def __init__(self, model_dir: str = MODEL_DIR):
        self.model_dir = model_dir
        self.m_start = None
        self.m_mins = None
        self.m_60 = None
        self.m_0 = None
        self.is_loaded = False
        self._load_models()

    def _load_models(self):
        try:
            p_start_path = os.path.join(self.model_dir, "minutes_start_v1.pkl")
            p_mins_path = os.path.join(self.model_dir, "minutes_regression_v1.pkl")
            p_60_path = os.path.join(self.model_dir, "minutes_60plus_v1.pkl")
            p_0_path = os.path.join(self.model_dir, "minutes_zero_v1.pkl")

            if (os.path.exists(p_start_path) and os.path.exists(p_mins_path) and
                os.path.exists(p_60_path) and os.path.exists(p_0_path)):
                with open(p_start_path, "rb") as f: self.m_start = pickle.load(f)
                with open(p_mins_path, "rb") as f: self.m_mins = pickle.load(f)
                with open(p_60_path, "rb") as f: self.m_60 = pickle.load(f)
                with open(p_0_path, "rb") as f: self.m_0 = pickle.load(f)
                self.is_loaded = True
                logger.info("Successfully loaded expected minutes ML models.")
            else:
                logger.warning("ML model pickle files missing. Fallback enabled.")
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}. Fallback enabled.")
            self.is_loaded = False

    def get_fallback_prediction(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        """Compute deterministic baseline availability predictions as fallback."""
        avg_mins = float(pdata.get("average_minutes_last_5", pdata.get("minutes_last_1", 60.0)))
        starts = float(pdata.get("starts_last_5", 3.0))
        apps = float(pdata.get("appearances_last_5", 4.0))
        bench_apps = float(pdata.get("bench_appearances_last_5", 1.0))
        unused = float(pdata.get("unused_substitute_last_5", 0.0))

        p_start = float(np.clip(starts / 5.0, 0.05, 0.95))
        p_60 = float(np.clip((max(0, apps - bench_apps)) / 5.0, 0.05, 0.95))
        p_0 = float(np.clip(unused / 5.0, 0.05, 0.95))

        return {
            "expected_minutes": round(avg_mins, 1),
            "p_start": round(p_start, 3),
            "p_60_plus": round(p_60, 3),
            "p_zero": round(p_0, 3),
            "model_version": "expected_minutes_baseline_v1",
            "used_fallback": True
        }

    def predict(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        """Predict expected minutes and availability probabilities using ML models or fallback."""
        if not self.is_loaded:
            return self.get_fallback_prediction(pdata)

        try:
            # Construct feature DataFrame
            feat_dict = {}
            for col in FEATURE_COLS:
                feat_dict[col] = [float(pdata.get(col, 0.0))]

            df_feat = pd.DataFrame(feat_dict)

            # Predict ML outcomes
            p_start = float(np.clip(self.m_start.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))
            raw_mins = float(self.m_mins.predict(df_feat)[0])
            exp_mins = float(np.clip(raw_mins, 0.0, 180.0))
            p_60 = float(np.clip(self.m_60.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))
            p_0 = float(np.clip(self.m_0.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))

            return {
                "expected_minutes": round(exp_mins, 1),
                "p_start": round(p_start, 3),
                "p_60_plus": round(p_60, 3),
                "p_zero": round(p_0, 3),
                "model_version": "expected_minutes_v1",
                "used_fallback": False
            }
        except Exception as e:
            logger.error(f"Inference error for player data: {e}. Utilizing fallback.")
            return self.get_fallback_prediction(pdata)

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Vectorized batch prediction of expected minutes & availability for a DataFrame."""
        if not self.is_loaded:
            df_res = df.copy()
            df_res["expected_minutes_v1"] = df_res["average_minutes_last_5"]
            df_res["p_start"] = (df_res["starts_last_5"] / 5.0).clip(0.05, 0.95)
            df_res["p_60_plus"] = (df_res["starts_last_5"] / 5.0).clip(0.05, 0.95)
            df_res["p_zero"] = 0.1
            return df_res

        df_res = df.copy()
        feat_df = pd.DataFrame()
        for c in FEATURE_COLS:
            if c in df_res.columns:
                feat_df[c] = df_res[c].astype(float)
            elif c == 'home_away_is_home':
                feat_df[c] = (df_res.get('home_away', 'H') == 'H').astype(float)
            elif c.startswith('pos_'):
                pos_target = c.replace('pos_', '')
                feat_df[c] = (df_res.get('position', 'MID') == pos_target).astype(float)
            else:
                feat_df[c] = 0.0

        p_start = np.clip(self.m_start.predict_proba(feat_df)[:, 1], 0.0, 1.0)
        raw_mins = self.m_mins.predict(feat_df)
        exp_mins = np.clip(raw_mins, 0.0, 90.0)
        p_60 = np.clip(self.m_60.predict_proba(feat_df)[:, 1], 0.0, 1.0)
        p_0 = np.clip(self.m_0.predict_proba(feat_df)[:, 1], 0.0, 1.0)

        df_res["expected_minutes_v1"] = np.round(exp_mins, 2)
        df_res["p_start"] = np.round(p_start, 4)
        df_res["p_60_plus"] = np.round(p_60, 4)
        df_res["p_zero"] = np.round(p_0, 4)

        return df_res
