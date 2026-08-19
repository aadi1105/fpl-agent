import logging
import numpy as np
from typing import Dict, Any

logger = logging.getLogger("xa_candidate_v2")

# Position xA/90 Priors learned from 2022-25 training data
XA_POSITION_PRIORS = {
    'FWD': 0.140,
    'MID': 0.180,
    'DEF': 0.090,
    'GKP': 0.010
}

# Empirical Bayesian Shrinkage Half-Life (M0 = 600 mins)
M0_XA_MINS = 600.0

class XACandidateV2:
    """
    Candidate V2 Expected Assists (xA) Predictor (Phase 3C.8)
    - Combines multi-window temporal recency (last 5, 10 xA/90 + Creativity/90) with career prior.
    - Applies empirical Bayesian sample-size shrinkage (M0 = 600 mins).
    - Prevents extreme small-sample extrapolation for low-minute players.
    """
    def __init__(self, m0_mins: float = M0_XA_MINS):
        self.m0_mins = m0_mins
        
    def calculate_shrunk_xa90(
        self,
        raw_xa90_multiwindow: float,
        career_mins: float,
        pos: str = 'MID'
    ) -> Dict[str, Any]:
        """
        Calculate sample-size-aware shrunk xA/90 using Empirical Bayes weighting.
        """
        prior_xa90 = XA_POSITION_PRIORS.get(pos, 0.150)
        mins = float(max(0.0, career_mins))
        
        # Empirical Bayes weight w = N / (N + M0)
        w_evidence = mins / (mins + self.m0_mins)
        
        # Bayesian Shrunk Rate
        shrunk_rate = (w_evidence * raw_xa90_multiwindow) + ((1.0 - w_evidence) * prior_xa90)
        
        return {
            'shrunk_xa90': round(float(shrunk_rate), 4),
            'w_evidence': round(float(w_evidence), 3),
            'prior_xa90': prior_xa90,
            'raw_xa90': round(float(raw_xa90_multiwindow), 4),
            'model_version': 'xa_candidate_v2'
        }
