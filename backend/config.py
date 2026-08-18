import os
try:
    from pydantic_settings import BaseSettings
except ImportError:
    BaseSettings = object

class Settings:
    PROJECT_NAME: str = "FPL 2026/27 Decision Engine"
    API_V1_STR: str = "/api/v1"
    MODEL_VERSION: str = "Hybrid Statistical + ML Engine v1.0"
    
    # FPL API Base URL
    FPL_API_BASE_URL: str = "https://fantasy.premierleague.com/api"
    
    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fpl_engine.db')}"
    )
    
    # Model Weights for Ensemble
    WEIGHT_INTERNAL: float = 0.40
    WEIGHT_FPL_REVIEW: float = 0.30
    WEIGHT_FFS: float = 0.20
    WEIGHT_FFFIX: float = 0.10
    
    # Default Optimization Horizon Weights (Current GW + 3)
    # GW0: 55%, GW1: 20%, GW2: 15%, GW3: 10%
    DEFAULT_HORIZON_WEIGHTS: list = [0.55, 0.20, 0.15, 0.10]
    
    # 2026/27 FPL Rules Configuration
    DEFCON_DEFENDER_THRESHOLD: int = 10  # CBIT threshold for 2pts in 2026/27
    DEFCON_POINTS: int = 2
    DEFCON_MAX_POINTS: int = 2
    
    # Default Budget & Squad Constraints
    TOTAL_BUDGET: int = 1000  # £100.0m represented in tenths
    MAX_PLAYERS_PER_TEAM: int = 3
    SQUAD_SIZE: int = 15
    
    POSITION_COUNTS = {
        "GKP": 2,
        "DEF": 5,
        "MID": 5,
        "FWD": 3
    }
    
    STARTING_FORMATION_LIMITS = {
        "GKP": (1, 1),
        "DEF": (3, 5),
        "MID": (2, 5),
        "FWD": (1, 3)
    }

settings = Settings()
