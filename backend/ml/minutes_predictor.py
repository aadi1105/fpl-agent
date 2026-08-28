import os
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple

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
            v2_path = os.path.join(self.model_dir, "expected_minutes_v2.pkl")
            p_start_path = os.path.join(self.model_dir, "minutes_start_v1.pkl")
            p_mins_path = os.path.join(self.model_dir, "minutes_regression_v1.pkl")
            p_60_path = os.path.join(self.model_dir, "minutes_60plus_v1.pkl")
            p_0_path = os.path.join(self.model_dir, "minutes_zero_v1.pkl")

            if os.path.exists(v2_path) and os.path.exists(p_start_path) and os.path.exists(p_mins_path):
                with open(v2_path, "rb") as f: self.v2_cfg = pickle.load(f)
                with open(p_start_path, "rb") as f: self.m_start = pickle.load(f)
                with open(p_mins_path, "rb") as f: self.m_mins = pickle.load(f)
                with open(p_60_path, "rb") as f: self.m_60 = pickle.load(f)
                with open(p_0_path, "rb") as f: self.m_0 = pickle.load(f)
                self.is_loaded = True
                self.model_version = "expected_minutes_v2"
                logger.info("Successfully loaded Expected Minutes v2 production model.")
            elif (os.path.exists(p_start_path) and os.path.exists(p_mins_path) and
                os.path.exists(p_60_path) and os.path.exists(p_0_path)):
                with open(p_start_path, "rb") as f: self.m_start = pickle.load(f)
                with open(p_mins_path, "rb") as f: self.m_mins = pickle.load(f)
                with open(p_60_path, "rb") as f: self.m_60 = pickle.load(f)
                with open(p_0_path, "rb") as f: self.m_0 = pickle.load(f)
                self.is_loaded = True
                self.model_version = "expected_minutes_v1"
                logger.info("Successfully loaded Expected Minutes v1 model.")
            else:
                logger.warning("ML model pickle files missing. Fallback enabled.")
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}. Fallback enabled.")
            self.is_loaded = False

    def get_fallback_prediction(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        """Compute deterministic baseline availability predictions as fallback."""
        mins_last_5 = float(pdata.get("minutes_last_5", pdata.get("average_minutes_last_5", 0.0) * 5.0))
        starts_last_5 = float(pdata.get("starts_last_5", 0.0))
        apps_last_5 = float(pdata.get("appearances_last_5", pdata.get("starts_last_5", 0.0)))
        unused = float(pdata.get("unused_substitute_last_5", 0.0))

        sample_games = min(5.0, max(apps_last_5, mins_last_5 / 90.0))
        w_evidence = sample_games / 5.0

        p_start = float(np.clip((w_evidence * (starts_last_5 / 5.0)) + ((1.0 - w_evidence) * 0.10), 0.05, 0.95))
        p_60 = float(np.clip((w_evidence * (starts_last_5 / 5.0)) + ((1.0 - w_evidence) * 0.05), 0.05, 0.95))
        p_0 = float(np.clip((w_evidence * (unused / 5.0)) + ((1.0 - w_evidence) * 0.70), 0.05, 0.95))
        
        if w_evidence <= 0.0 and "average_minutes_last_5" in pdata:
            avg_mins = float(pdata["average_minutes_last_5"])
        else:
            avg_mins = (w_evidence * (mins_last_5 / max(1.0, apps_last_5))) + ((1.0 - w_evidence) * 15.0)

        return {
            "expected_minutes": round(avg_mins, 1),
            "p_start": round(p_start, 3),
            "p_60_plus": round(p_60, 3),
            "p_zero": round(p_0, 3),
            "model_version": "expected_minutes_baseline_v1",
            "used_fallback": True
        }

    def _apply_role_evidence_shrinkage(
        self,
        raw_mins: float,
        raw_p_start: float,
        raw_p_60: float,
        raw_p_0: float,
        pdata: Dict[str, Any]
    ) -> Tuple[float, float, float, float]:
        """
        Empirical Role Evidence Shrinkage:
        Shrinks raw ML predictions towards a conservative prior when recent current-club role evidence is sparse.
        """
        mins_last_5 = float(pdata.get("minutes_last_5", 0.0))
        apps_last_5 = float(pdata.get("appearances_last_5", 0.0))
        starts_last_5 = float(pdata.get("starts_last_5", 0.0))

        # Sample weight w_evidence in [0.0, 1.0] based on actual recent playing sample
        sample_games = min(5.0, max(apps_last_5, mins_last_5 / 90.0))
        w_evidence = sample_games / 5.0

        price = float(pdata.get("price", 5.0))
        is_gkp = float(pdata.get("pos_DEF", 0.0)) == 0 and float(pdata.get("pos_MID", 0.0)) == 0 and float(pdata.get("pos_FWD", 0.0)) == 0

        # Dynamic price & role-aware prior when recent 5-game sample is sparse
        if is_gkp and price >= 4.5:
            prior_mins, prior_p_start, prior_p_60, prior_p_zero = 85.0, 0.90, 0.90, 0.10
        elif price >= 9.0:
            prior_mins, prior_p_start, prior_p_60, prior_p_zero = 75.0, 0.85, 0.80, 0.10
        elif price >= 7.0:
            prior_mins, prior_p_start, prior_p_60, prior_p_zero = 65.0, 0.75, 0.70, 0.15
        elif price >= 5.5:
            prior_mins, prior_p_start, prior_p_60, prior_p_zero = 55.0, 0.60, 0.50, 0.25
        else:
            prior_mins, prior_p_start, prior_p_60, prior_p_zero = 25.0, 0.25, 0.15, 0.60

        calibrated_mins = (w_evidence * raw_mins) + ((1.0 - w_evidence) * prior_mins)
        calibrated_p_start = (w_evidence * raw_p_start) + ((1.0 - w_evidence) * prior_p_start)
        calibrated_p_60 = (w_evidence * raw_p_60) + ((1.0 - w_evidence) * prior_p_60)
        calibrated_p_zero = (w_evidence * raw_p_0) + ((1.0 - w_evidence) * prior_p_zero)

        return calibrated_mins, calibrated_p_start, calibrated_p_60, calibrated_p_zero

    def predict(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        """Predict expected minutes and availability probabilities using ML models or fallback."""
        if not self.is_loaded:
            return self.get_fallback_prediction(pdata)

        try:
            # Construct feature DataFrame with smart rolling feature imputation
            mins_5 = float(pdata.get("minutes_last_5", pdata.get("average_minutes_last_5", 0.0) * 5.0))
            starts_5 = float(pdata.get("starts_last_5", 0.0))
            apps_5 = float(pdata.get("appearances_last_5", starts_5))

            feat_dict = {}
            for col in FEATURE_COLS:
                if col in pdata:
                    feat_dict[col] = [float(pdata[col])]
                elif col == 'minutes_last_1':
                    feat_dict[col] = [float(min(90.0, pdata.get('average_minutes_last_5', mins_5 / max(1.0, apps_5))))]
                elif col == 'minutes_last_3':
                    feat_dict[col] = [float(min(270.0, mins_5 * 0.6))]
                elif col == 'minutes_last_10':
                    feat_dict[col] = [float(mins_5 * 2.0)]
                elif col == 'starts_last_1':
                    feat_dict[col] = [1.0 if starts_5 >= 1.0 else 0.0]
                elif col == 'starts_last_3':
                    feat_dict[col] = [float(min(3.0, starts_5 * 0.6))]
                elif col == 'starts_last_10':
                    feat_dict[col] = [float(starts_5 * 2.0)]
                elif col == 'average_minutes_last_5':
                    feat_dict[col] = [float(mins_5 / max(1.0, apps_5)) if apps_5 > 0 else 0.0]
                elif col == 'average_minutes_last_10':
                    feat_dict[col] = [float(mins_5 / max(1.0, apps_5)) if apps_5 > 0 else 0.0]
                elif col == 'appearances_last_5':
                    feat_dict[col] = [apps_5]
                elif col == 'minutes_last_5':
                    feat_dict[col] = [mins_5]
                elif col == 'starts_last_5':
                    feat_dict[col] = [starts_5]
                else:
                    feat_dict[col] = [0.0]

            df_feat = pd.DataFrame(feat_dict)

            # Predict raw ML outcomes
            raw_p_start = float(np.clip(self.m_start.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))
            raw_mins = float(np.clip(self.m_mins.predict(df_feat)[0], 0.0, 90.0))
            raw_p_60 = float(np.clip(self.m_60.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))
            raw_p_0 = float(np.clip(self.m_0.predict_proba(df_feat)[:, 1][0], 0.0, 1.0))

            # Apply Empirical Role Evidence Shrinkage
            exp_mins, p_start, p_60, p_0 = self._apply_role_evidence_shrinkage(
                raw_mins, raw_p_start, raw_p_60, raw_p_0, pdata
            )

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
                home_series = df_res['home_away'] if 'home_away' in df_res.columns else pd.Series(['H'] * len(df_res))
                feat_df[c] = (home_series == 'H').astype(float)
            elif c.startswith('pos_'):
                pos_target = c.replace('pos_', '')
                pos_series = df_res['position'] if 'position' in df_res.columns else pd.Series(['MID'] * len(df_res))
                feat_df[c] = (pos_series == pos_target).astype(float)
            else:
                feat_df[c] = 0.0

        p_start_raw = np.clip(self.m_start.predict_proba(feat_df)[:, 1], 0.0, 1.0)
        mins_raw = np.clip(self.m_mins.predict(feat_df), 0.0, 90.0)
        p_60_raw = np.clip(self.m_60.predict_proba(feat_df)[:, 1], 0.0, 1.0)
        p_0_raw = np.clip(self.m_0.predict_proba(feat_df)[:, 1], 0.0, 1.0)

        # Apply Vectorized Role Evidence Shrinkage
        apps_last_5 = df_res['appearances_last_5'].astype(float) if 'appearances_last_5' in df_res.columns else 0.0
        mins_last_5 = df_res['minutes_last_5'].astype(float) if 'minutes_last_5' in df_res.columns else 0.0
        sample_games = np.minimum(5.0, np.maximum(apps_last_5, mins_last_5 / 90.0))
        w_evidence = sample_games / 5.0

        exp_mins = (w_evidence * mins_raw) + ((1.0 - w_evidence) * 15.0)
        p_start = (w_evidence * p_start_raw) + ((1.0 - w_evidence) * 0.10)
        p_60 = (w_evidence * p_60_raw) + ((1.0 - w_evidence) * 0.05)
        p_0 = (w_evidence * p_0_raw) + ((1.0 - w_evidence) * 0.70)

        df_res["expected_minutes_v1"] = np.round(exp_mins, 2)
        df_res["p_start"] = np.round(p_start, 4)
        df_res["p_60_plus"] = np.round(p_60, 4)
        df_res["p_zero"] = np.round(p_0, 4)

        return df_res
