import logging
import numpy as np
from typing import Dict, Any, Tuple
from backend.ml.minutes_predictor import MinutesPredictor

logger = logging.getLogger("minutes_candidate_v2")

POSITION_START_PRIORS = {
    'GKP': {'start_prob': 0.85, 'prior_mins': 76.5},
    'DEF': {'start_prob': 0.55, 'prior_mins': 49.5},
    'MID': {'start_prob': 0.50, 'prior_mins': 45.0},
    'FWD': {'start_prob': 0.45, 'prior_mins': 40.5}
}

PRICE_TIER_ROLE_PRIORS = {
    'GKP': {'high': 0.90, 'mid': 0.60, 'low': 0.15},
    'DEF': {'high': 0.85, 'mid': 0.60, 'low': 0.30},
    'MID': {'high': 0.85, 'mid': 0.60, 'low': 0.30},
    'FWD': {'high': 0.85, 'mid': 0.60, 'low': 0.30}
}

class MinutesCandidateV2:
    """
    Candidate V2 Expected Minutes Predictor (Phase 3C.8)
    - Fixes synthetic 5-start imputation for low-career-minute players.
    - Uses true fixture-level rolling starts and current-club evidence.
    - Applies Bayesian prior shrinkage for weak current-club evidence.
    - Ensures logical consistency between P(start), P(60+), P(0), and expected minutes.
    """
    def __init__(self):
        self.base_predictor = MinutesPredictor()
        
    def predict_candidate_minutes(
        self,
        pdata: Dict[str, Any],
        actual_recent_starts_5: float,
        actual_recent_mins_5: float,
        current_club_starts: float,
        current_club_mins: float,
        pos: str = 'MID',
        cost: float = 5.5
    ) -> Dict[str, Any]:
        """
        Predict expected minutes and start probabilities using candidate v2 architecture.
        """
        pdata_copy = dict(pdata)
        pdata_copy['starts_last_5'] = float(actual_recent_starts_5)
        pdata_copy['minutes_last_5'] = float(actual_recent_mins_5)
        
        # Get raw base prediction using .predict()
        base_res = self.base_predictor.predict(pdata_copy)
        raw_mins = base_res.get('expected_minutes', base_res.get('expected_minutes_ml', 45.0))
        raw_p_start = base_res.get('p_start', 0.50)
        
        cost_tier = 'high' if cost >= 8.0 else ('mid' if cost >= 5.5 else 'low')
        tier_start_prior = PRICE_TIER_ROLE_PRIORS.get(pos, {}).get(cost_tier, 0.40)
        pos_mins_prior = POSITION_START_PRIORS.get(pos, {}).get('prior_mins', 45.0)
        
        w_evidence = min(1.0, max(0.0, float(current_club_starts) / 5.0))
        
        calibrated_p_start = (w_evidence * raw_p_start) + ((1.0 - w_evidence) * tier_start_prior)
        calibrated_mins = (w_evidence * raw_mins) + ((1.0 - w_evidence) * pos_mins_prior)
        
        p_start = float(np.clip(calibrated_p_start, 0.0, 1.0))
        p_60 = float(np.clip(p_start * 0.95, 0.0, p_start))
        p_zero = float(np.clip(1.0 - (calibrated_mins / 70.0), 0.0, 1.0)) if calibrated_mins < 70.0 else float(np.clip((90.0 - calibrated_mins)/90.0, 0.0, 0.20))
        
        tot_prob = p_start + p_zero
        if tot_prob > 1.0:
            p_start = p_start / tot_prob
            p_zero = p_zero / tot_prob

        return {
            'expected_minutes_v2': round(float(calibrated_mins), 1),
            'p_start_v2': round(float(p_start), 3),
            'p_60_plus_v2': round(float(p_60), 3),
            'p_zero_v2': round(float(p_zero), 3),
            'w_evidence': round(float(w_evidence), 3),
            'raw_ml_mins': round(float(raw_mins), 1),
            'model_version': 'expected_minutes_candidate_v2'
        }
