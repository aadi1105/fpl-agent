from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class IngestionResponse(BaseModel):
    status: str
    synced: Dict[str, int]

class ProjectionRunRequest(BaseModel):
    start_gw: int = Field(default=1, ge=1, le=38)
    end_gw: int = Field(default=8, ge=1, le=38)
    source: str = Field(default="internal")

class ProjectionRunResponse(BaseModel):
    status: str
    records_updated: int
    start_gw: int
    end_gw: int

class OptimizationRequest(BaseModel):
    mode: str = Field(
        default="CURRENT_GW_PLUS_3",
        description="Optimization Mode: CURRENT_GW_PLUS_3, STRONG_XI_DUMP_BENCH, BALANCED_BENCH, MAXIMUM_SQUAD"
    )
    current_gw: int = Field(default=1, ge=1, le=38)
    total_budget: int = Field(default=1000, description="Budget in tenths (£100.0m = 1000)")
    max_players_per_team: int = Field(default=3)
    projection_source: str = Field(default="internal")
    weights: Optional[List[float]] = Field(default=None, description="Custom 4-GW weights [GW0, GW1, GW2, GW3]")
    banned_player_ids: Optional[List[int]] = Field(default_factory=list)
    locked_player_ids: Optional[List[int]] = Field(default_factory=list)

class PlayerSummary(BaseModel):
    id: int
    web_name: str
    first_name: Optional[str] = None
    second_name: Optional[str] = None
    element_type: str
    team_id: int
    team_name: str
    now_cost: int
    now_cost_str: str
    gw0_xp: float = 0.0
    gw1_xp: float = 0.0
    gw2_xp: float = 0.0
    gw3_xp: float = 0.0
    weighted_xp: float = 0.0
    expected_points_total: float = 0.0
    expected_points_per_gw: float = 0.0
    expected_points: Optional[float] = 0.0
    is_starter: bool
    is_captain: bool
    is_vice_captain: bool

class OptimizationResponse(BaseModel):
    model_version: str = "Baseline Projection Model v0.2 (Deterministic / Statistical)"
    optimization_mode: str
    current_gw: int
    horizon_weights: List[float]
    total_budget: int
    total_cost: int
    total_cost_str: str
    bank: int
    bank_str: str
    current_gw_starting_xi_xp: float
    captain_contribution_xp: float
    total_current_gw_xp: float
    weighted_horizon_xp: float
    captain: Optional[PlayerSummary] = None
    vice_captain: Optional[PlayerSummary] = None
    starting_11: List[PlayerSummary]
    bench: List[PlayerSummary]
    squad_count: int
    anomalies: List[str] = Field(default_factory=list)
    explanations: List[str] = Field(default_factory=list)
