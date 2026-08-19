import logging
import numpy as np
from typing import Dict, Any

logger = logging.getLogger("xg_candidate_v2")

# Position xG/90 Priors learned from 2022-25 training data
XG_POSITION_PRIORS = {
    'FWD': 0.380,
    'MID': 0.220,
    'DEF': 0.060,
    'GKP': 0.000
}

# Empirical Bayesian Shrinkage Half-Life (M0 = 750 mins)
M0_XG_MINS = 750.0

class XGCandidateV2:
    """
    Candidate V2 Expected Goals (xG) Predictor (Phase 3C.8)
    - Combines multi-window temporal recency (last 3, 5, 10 xG/90 + Threat/90) with career prior.
    - Applies empirical Bayesian sample-size shrinkage (M0 = 750 mins).
    - Prevents extreme small-sample extrapolation for low-minute players.
    """
    def __init__(self, m0_mins: float = M0_XG_MINS):
        self.m0_mins = m0_mins
        
    def calculate_shrunk_xg90(
        self,
        raw_xg90_multiwindow: float,
        career_mins: float,
        pos: str = 'MID'
    ) -> Dict[str, Any]:
        """
        Calculate sample-size-aware shrunk xG/90 using Empirical Bayes weighting.
        """
        prior_xg90 = XG_POSITION_PRIORS.get(pos, 0.200)
        mins = float(max(0.0, career_mins))
        
        # Empirical Bayes weight w = N / (N + M0)
        w_evidence = mins / (mins + self.m0_mins)
        
        # Bayesian Shrunk Rate
        shrunk_rate = (w_evidence * raw_xg90_multiwindow) + ((1.0 - w_evidence) * prior_xg90)
        
        return {
            'shrunk_xg90': round(float(shrunk_rate), 4),
            'w_evidence': round(float(w_evidence), 3),
            'prior_xg90': prior_xg90,
            'raw_xg90': round(float(raw_xg90_multiwindow), 4),
            'model_version': 'xg_candidate_v2'
        }
