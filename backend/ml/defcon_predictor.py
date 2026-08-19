import math
import logging
from typing import Dict, Any

logger = logging.getLogger("defcon_predictor")

MODEL_VERSION = "defcon_v1_poisson"

class DEFCONPredictor:
    """Predictor wrapper for 2026/27 DEFCON Probability Poisson Model."""
    def __init__(self):
        self.version = MODEL_VERSION

    def calculate_poisson_probability(self, mean_lambda: float, threshold: int) -> float:
        """Calculate P(X >= threshold) for a Poisson distribution with parameter mean_lambda."""
        if mean_lambda <= 0.0:
            return 0.0
            
        prob_under_threshold = 0.0
        for k in range(threshold):
            prob_under_threshold += (math.pow(mean_lambda, k) * math.exp(-mean_lambda)) / math.factorial(k)

        prob_at_least_threshold = 1.0 - prob_under_threshold
        return round(min(0.85, max(0.0, prob_at_least_threshold)), 3)

    def predict(self, pdata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict 2026/27 DEFCON probability:
        - DEF: 10 combined Clearances, Blocks, Interceptions, Tackles (CBIT)
        - MID / FWD: 12 combined CBIT + Recoveries (CBIRT)
        """
        pos = pdata.get("position", "DEF")
        mins_ratio = float(pdata.get("expected_minutes_v1", 60.0)) / 90.0
        cbit90 = float(pdata.get("cbit90", 4.0))
        opp_att_rating = float(pdata.get("opponent_attack_rating", 1000.0))

        cbit_multiplier = min(1.80, max(0.50, opp_att_rating / 1000.0))
        
        if pos == "DEF":
            expected_cbit = cbit90 * mins_ratio * cbit_multiplier
            defcon_prob = self.calculate_poisson_probability(expected_cbit, 10)
        elif pos in ["MID", "FWD"]:
            cbirt90 = cbit90 + (3.0 if pos == "MID" else 1.5) # Include recoveries for MID/FWD
            expected_cbirt = cbirt90 * mins_ratio * cbit_multiplier
            defcon_prob = self.calculate_poisson_probability(expected_cbirt, 12)
        else:
            defcon_prob = 0.0

        return {
            "defcon_probability": defcon_prob,
            "model_version": MODEL_VERSION,
            "used_fallback": False
        }
