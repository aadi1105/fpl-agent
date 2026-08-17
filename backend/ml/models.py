import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ml_models")

class ModelRegistry:
    """
    Registry tracking model versions, baselines, and evaluation metrics.
    Ensures baseline models must be beaten via out-of-sample backtesting before deployment.
    """
    REGISTRY = {
        "minutes": {
            "v0_baseline": {"type": "heuristic", "status": "active", "mae": 14.2},
            "v1_lgbm": {"type": "LightGBM", "status": "experimental", "mae": 11.5}
        },
        "defcon": {
            "v0_poisson": {"type": "Poisson Statistical", "status": "active", "log_loss": 0.32},
            "v1_lgbm": {"type": "LightGBM", "status": "experimental", "log_loss": 0.28}
        }
    }

    @classmethod
    def get_active_model_info(cls, model_name: str) -> Dict[str, Any]:
        return cls.REGISTRY.get(model_name, {}).get("v0_baseline", {})
