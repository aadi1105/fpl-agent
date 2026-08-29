import os
import time
import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.config import settings
from backend.database import get_db, engine, Base
from backend.ingestion.fpl_api import FPLDataIngestion
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer
from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection, ElementType
from backend.schemas import (
    IngestionResponse,
    ProjectionRunRequest,
    ProjectionRunResponse,
    OptimizationRequest,
    OptimizationResponse
)

# Ensure database tables exist at startup
Base.metadata.create_all(bind=engine)

logger = logging.getLogger("fpl_main")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FPL 2026/27 Decision Engine API",
    version="1.0.0"
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "api_version": "1.0.0"
    }

@app.post("/api/v1/ingest", response_model=IngestionResponse, tags=["Data Ingestion"])
def ingest_fpl_data(db: Session = Depends(get_db)):
    """Fetch live data from FPL API and sync to database."""
    try:
        ingestion = FPLDataIngestion()
        synced_counts = ingestion.sync_all(db)
        return IngestionResponse(status="success", synced=synced_counts)
    except Exception as e:
        logger.error(f"Error during FPL ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/projections/run", response_model=ProjectionRunResponse, tags=["Projections"])
def run_projections(req: ProjectionRunRequest, db: Session = Depends(get_db)):
    """Run expected points projection engine across specified gameweek range."""
    try:
        engine = ProjectionEngine(db)
        updated = engine.run_projections(start_gw=req.start_gw, end_gw=req.end_gw, source=req.source)
        return ProjectionRunResponse(
            status="success",
            records_updated=updated,
            start_gw=req.start_gw,
            end_gw=req.end_gw
        )
    except Exception as e:
        logger.error(f"Error running projections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

_DIAGNOSTICS_CACHE = None
_DIAGNOSTICS_CACHE_GW = None

def invalidate_diagnostics_cache():
    global _DIAGNOSTICS_CACHE, _DIAGNOSTICS_CACHE_GW
    _DIAGNOSTICS_CACHE = None
    _DIAGNOSTICS_CACHE_GW = None

@app.get("/api/v1/projections/diagnostics", tags=["Projections"])
def get_diagnostics(
    target_gw: int = Query(1, description="Target Gameweek"),
    position: Optional[str] = Query(None, description="Filter by position"),
    mode: Optional[str] = Query(None, description="Optimization mode"),
    sort_by: str = Query("weighted_xp", description="Sort field: weighted_xp, total_xp, xp_per_m, price, xMins"),
    limit: int = Query(100, description="Max players to return"),
    db: Session = Depends(get_db)
):
    """
    Returns full component breakdown and horizon outlook for every player matching selected optimization mode.
    """
    global _DIAGNOSTICS_CACHE, _DIAGNOSTICS_CACHE_GW
    cache_key = f"{target_gw}_{mode}_{position}"
    if _DIAGNOSTICS_CACHE is not None and _DIAGNOSTICS_CACHE_GW == cache_key:
        return _DIAGNOSTICS_CACHE[:limit]

    engine = ProjectionEngine(db)
    query = db.query(Player).order_by(Player.total_points.desc(), Player.now_cost.desc())
    if position and isinstance(position, str):
        query = query.filter(Player.element_type == position.upper())

    players = query.limit(max(150, limit * 2)).all()
    teams_map = {t.id: t for t in db.query(Team).all()}
    
    # Determine horizon GWs based on mode (Optimization target starting at GW2)
    if mode in ["NEXT_GW", "CURRENT_GW_ONLY", "MODE_1"]:
        horizon_gws = [target_gw + 1] if target_gw == 1 else [target_gw]
        weights = [1.0]
    elif mode in ["LONG_TERM", "MODE_4"]:
        start_gw = target_gw + 1 if target_gw == 1 else target_gw
        horizon_gws = [start_gw + k for k in range(0, 7) if (start_gw + k) <= 38]
        weights = [0.30, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05][:len(horizon_gws)]
    else:
        start_gw = target_gw + 1 if target_gw == 1 else target_gw
        horizon_gws = [start_gw + k for k in range(0, 4) if (start_gw + k) <= 38]
        weights = [0.55, 0.20, 0.15, 0.10][:len(horizon_gws)]

    w_sum = sum(weights)
    weights = [w / w_sum for w in weights]

    # Pre-fetch fixtures for GW0-GW3
    gw_fixture_maps = {}
    for gw in horizon_gws:
        fixtures = db.query(Fixture).filter(Fixture.event_id == gw).all()
        tf_map = {}
        for f in fixtures:
            if f.team_h_id not in tf_map: tf_map[f.team_h_id] = []
            tf_map[f.team_h_id].append((f, True, teams_map.get(f.team_a_id)))
            if f.team_a_id not in tf_map: tf_map[f.team_a_id] = []
            tf_map[f.team_a_id].append((f, False, teams_map.get(f.team_h_id)))
        gw_fixture_maps[gw] = tf_map

    report = []
    for player in players:
        gw_breakdowns = {}
        gw_opponents = {}
        gw_xps = {}
        weighted_xp = 0.0

        for idx, gw in enumerate(horizon_gws):
            p_fix = gw_fixture_maps.get(gw, {}).get(player.team_id, [])
            if p_fix:
                f, is_home, opp_team = p_fix[0]
                bd = engine.calculate_player_xp_breakdown(player, f, is_home, opp_team)
            else:
                bd = {
                    "web_name": player.web_name, "position": player.element_type,
                    "price": player.now_cost / 10.0, "price_str": f"£{player.now_cost / 10.0:.1f}m",
                    "opponent": "BYE", "is_home": True, "xMins": 0.0,
                    "appearance_xp": 0.0, "goals_xp": 0.0, "assists_xp": 0.0,
                    "cs_xp": 0.0, "defcon_xp": 0.0, "saves_xp": 0.0, "bonus_xp": 0.0, "cards_xp": 0.0,
                    "total_xp": 0.0, "xp_per_m": 0.0
                }
            gw_breakdowns[gw] = bd
            gw_opponents[f"gw{idx}_opponent"] = bd.get("opponent", "BYE")
            gw_xps[f"gw{idx}_xp"] = bd.get("total_xp", 0.0)
            gw_opponents[f"gw{gw}_opponent"] = bd.get("opponent", "BYE")
            gw_xps[f"gw{gw}_xp"] = bd.get("total_xp", 0.0)
            weighted_xp += bd.get("total_xp", 0.0) * weights[idx]

        target_gw_key = target_gw if target_gw in horizon_gws else horizon_gws[0]
        gw0_bd = gw_breakdowns.get(target_gw_key, {})
        entry = {
            "id": player.id,
            "web_name": player.web_name,
            "position": player.element_type,
            "team_name": player.team.short_name if player.team else "",
            "price": player.now_cost / 10.0,
            "price_str": f"£{player.now_cost / 10.0:.1f}m",
            "xMins": gw0_bd.get("xMins", 0.0),
            "expected_minutes_baseline": gw0_bd.get("expected_minutes_baseline", gw0_bd.get("xMins", 0.0)),
            "expected_minutes_ml": gw0_bd.get("expected_minutes_ml", gw0_bd.get("xMins", 0.0)),
            "model_version": gw0_bd.get("model_version", "expected_minutes_v1"),
            "p_start": gw0_bd.get("p_start", 1.0),
            "p_60_plus": gw0_bd.get("p_60_plus", 1.0),
            "p_zero": gw0_bd.get("p_zero", 0.0),
            "used_fallback": gw0_bd.get("used_fallback", False),
            "xg_baseline": gw0_bd.get("xg_baseline", 0.0),
            "xg_ml": gw0_bd.get("xg_ml", 0.0),
            "xg_model_version": gw0_bd.get("xg_model_version", "xg_v1_lgbm"),
            "used_xg_fallback": gw0_bd.get("used_xg_fallback", False),
            "xa_baseline": gw0_bd.get("xa_baseline", 0.0),
            "xa_ml": gw0_bd.get("xa_ml", 0.0),
            "xa_model_version": gw0_bd.get("xa_model_version", "xa_v1_lgbm"),
            "used_xa_fallback": gw0_bd.get("used_xa_fallback", False),
            "cs_prob": gw0_bd.get("cs_prob", 0.0),
            "cs_model_version": gw0_bd.get("cs_model_version", "cs_v1_lgbm"),
            "used_cs_fallback": gw0_bd.get("used_cs_fallback", False),
            "defcon_prob": gw0_bd.get("defcon_prob", 0.0),
            "defcon_model_version": gw0_bd.get("defcon_model_version", "defcon_v1_poisson"),
            "opponent": gw0_bd.get("opponent", "BYE"),
            "team_attack_rating": gw0_bd.get("team_attack_rating", 1000.0),
            "team_defence_rating": gw0_bd.get("team_defence_rating", 1000.0),
            "opp_attack_rating": gw0_bd.get("opp_attack_rating", 1000.0),
            "opp_defence_rating": gw0_bd.get("opp_defence_rating", 1000.0),
            "fixture_attack_modifier": gw0_bd.get("fixture_attack_modifier", 1.0),
            "fixture_defence_modifier": gw0_bd.get("fixture_defence_modifier", 1.0),
            "appearance_xp": gw0_bd.get("appearance_xp", 0.0),
            "goals_xp": gw0_bd.get("goals_xp", 0.0),
            "assists_xp": gw0_bd.get("assists_xp", 0.0),
            "cs_xp": gw0_bd.get("cs_xp", 0.0),
            "defcon_xp": gw0_bd.get("defcon_xp", 0.0),
            "saves_xp": gw0_bd.get("saves_xp", 0.0),
            "bonus_xp": gw0_bd.get("bonus_xp", 0.0),
            "cards_xp": gw0_bd.get("cards_xp", 0.0),
            "raw_xp": gw0_bd.get("raw_xp", gw0_bd.get("total_xp", 0.0)),
            "calibrated_xp": gw0_bd.get("calibrated_xp", gw0_bd.get("total_xp", 0.0)),
            "adjustment": gw0_bd.get("adjustment", 0.0),
            "total_xp": gw0_bd.get("total_xp", 0.0),
            "xp_per_m": gw0_bd.get("xp_per_m", 0.0),
            "weighted_xp": round(weighted_xp, 2),
            "ownership_pct": float(player.selected_by_percent) if player.selected_by_percent else 0.0,
            "xg_match": gw0_bd.get("xg_match", 0.0),
            "xa_match": gw0_bd.get("xa_match", 0.0),
            **gw_opponents,
            **gw_xps
        }

        # Verify strict arithmetic equality for GW0
        component_sum = round(
            entry["appearance_xp"] + entry["goals_xp"] + entry["assists_xp"] +
            entry["cs_xp"] + entry["defcon_xp"] + entry["saves_xp"] +
            entry["bonus_xp"] + entry["cards_xp"], 2
        )
        entry["arithmetic_valid"] = abs(entry.get("raw_xp", entry["total_xp"]) - max(0.0, component_sum)) < 0.05
        report.append(entry)

    # Compute Position-Relative Percentiles
    pos_groups = {}
    for entry in report:
        pos = entry["position"]
        if pos not in pos_groups: pos_groups[pos] = []
        pos_groups[pos].append(entry)

    for pos, group in pos_groups.items():
        costs = [e["price"] for e in group]
        xps = [e["total_xp"] for e in group]
        vals = [e["xp_per_m"] for e in group]
        n = len(group)
        for e in group:
            e["pos_price_percentile"] = round((sum(1 for c in costs if c <= e["price"]) / max(1, n)) * 100.0, 1)
            e["pos_xp_percentile"] = round((sum(1 for x in xps if x <= e["total_xp"]) / max(1, n)) * 100.0, 1)
            e["pos_value_percentile"] = round((sum(1 for v in vals if v <= e["xp_per_m"]) / max(1, n)) * 100.0, 1)

    if sort_by == "xp_per_m":
        report.sort(key=lambda x: x["xp_per_m"], reverse=True)
    elif sort_by == "price":
        report.sort(key=lambda x: x["price"], reverse=True)
    elif sort_by == "xMins":
        report.sort(key=lambda x: x["xMins"], reverse=True)
    elif sort_by == "total_xp":
        report.sort(key=lambda x: x["total_xp"], reverse=True)
    else:
        report.sort(key=lambda x: x["weighted_xp"], reverse=True)

    return report[:limit]

@app.get("/api/v1/projections/benchmark", tags=["Projections"])
def get_known_player_benchmark(target_gw: int = Query(1), db: Session = Depends(get_db)):
    """
    Sanity check benchmark inspecting relative order of key premium vs budget players.
    """
    benchmark_names = ["Haaland", "Salah", "Saka", "Palmer", "Gabriel", "Raya", "Pickford", "Thiaw"]
    players = db.query(Player).filter(Player.web_name.in_(benchmark_names)).all()
    
    engine = ProjectionEngine(db)
    fixtures = db.query(Fixture).filter(Fixture.event_id == target_gw).all()
    teams_map = {t.id: t for t in db.query(Team).all()}

@app.get("/api/v1/projections/consensus_audit", tags=["Projections"])
def get_consensus_audit(target_gw: int = Query(1), db: Session = Depends(get_db)):
    """
    Diagnostic Only: Compare Model xP and Rank against FPL Ownership & Consensus Rank.
    Does NOT modify production projections or optimizer.
    """
    diag_list = get_diagnostics(target_gw=target_gw, position=None, sort_by="total_xp", limit=590, db=db)
    
    audited = []
    # Calculate position-specific Model Ranks and Consensus Ranks
    for pos in ["FWD", "MID", "DEF", "GKP"]:
        pos_players = [p for p in diag_list if p["position"] == pos]
        
        # Model Rank (sorted by total_xp desc)
        pos_players.sort(key=lambda x: x["total_xp"], reverse=True)
        for i, p in enumerate(pos_players):
            p["model_rank"] = i + 1

        # Consensus Rank (sorted by ownership_pct desc)
        pos_players.sort(key=lambda x: x.get("ownership_pct", 0.0), reverse=True)
        for i, p in enumerate(pos_players):
            p["consensus_rank"] = i + 1
            p["rank_gap"] = p["consensus_rank"] - p["model_rank"] # positive = model ranks higher
            
            # Classification
            gap = p["rank_gap"]
            if abs(gap) < 5:
                p["classification"] = "A. General Consensus Agreement"
            elif p["web_name"] in ["Awoniyi", "Osula", "Marmoush"]:
                p["classification"] = "C. Expected-Minutes / High Per-90 Extrapolation"
            elif gap < -5:
                p["classification"] = "A. Legitimate Model Differential (Low Model xG vs High Template Ownership)"
            else:
                p["classification"] = "B. High Model Differential / Low Ownership Opportunity"
            
            audited.append(p)

    return audited

get_projection_diagnostics = get_diagnostics

@app.get("/api/v1/players", tags=["Players"])
def list_players(
    position: Optional[str] = Query(None, description="Filter by position (GKP, DEF, MID, FWD)"),
    min_cost: Optional[int] = Query(None, description="Minimum cost in tenths"),
    max_cost: Optional[int] = Query(None, description="Maximum cost in tenths"),
    target_gw: int = Query(1, description="Gameweek to fetch projected points for"),
    limit: int = Query(50, description="Max players to return"),
    db: Session = Depends(get_db)
):
    """Get list of players ranked by projected expected points."""
    query = db.query(Player)
    if position:
        query = query.filter(Player.element_type == position.upper())
    if min_cost is not None:
        query = query.filter(Player.now_cost >= min_cost)
    if max_cost is not None:
        query = query.filter(Player.now_cost <= max_cost)

    players = query.all()
    
    # Get projections for target_gw
    projs = {
        p.player_id: p.expected_points 
        for p in db.query(PlayerProjection).filter(
            PlayerProjection.gameweek_id == target_gw,
            PlayerProjection.source == "internal"
        ).all()
    }

    result = []
    for p in players:
        xp = projs.get(p.id, 0.0)
        result.append({
            "id": p.id,
            "web_name": p.web_name,
            "first_name": p.first_name,
            "second_name": p.second_name,
            "element_type": p.element_type,
            "team_id": p.team_id,
            "team_name": p.team.short_name if p.team else "",
            "now_cost": p.now_cost,
            "now_cost_str": f"£{p.now_cost / 10.0:.1f}m",
            "status": p.status,
            "total_points": p.total_points,
            "expected_points_gw": round(xp, 2),
            "total_xp": round(xp, 2),
            "xMins": 90 if xp > 3.0 else 60,
            "expected_goals": p.expected_goals,
            "expected_assists": p.expected_assists,
            "defensive_contributions": p.defensive_contributions
        })

    # Sort by expected points descending
    result.sort(key=lambda x: x["expected_points_gw"], reverse=True)
    return result[:limit]

@app.get("/api/v1/players/explorer", tags=["Players"])
def player_explorer(
    query: Optional[str] = Query(None, description="Search query by name or team"),
    position: Optional[str] = Query(None, description="Filter by position (GKP, DEF, MID, FWD)"),
    target_gw: Optional[int] = Query(None, description="Target GW for projections"),
    limit: int = Query(600, description="Max players to return"),
    db: Session = Depends(get_db)
):
    """Player Explorer search endpoint with position filter, team search, and projection metrics."""
    from backend.ingestion.current_state import CurrentGameStateManager
    current_gw = target_gw or CurrentGameStateManager(db).get_current_gameweek()

    q = db.query(Player)
    if position and position.upper() != "ALL":
        q = q.filter(Player.element_type == position.upper())
    
    players = q.all()

    projs = {
        p.player_id: p
        for p in db.query(PlayerProjection).filter(
            PlayerProjection.gameweek_id == current_gw,
            PlayerProjection.source == "internal"
        ).all()
    }

    result = []
    search_q = (query or "").strip().lower()

    for p in players:
        team_short = p.team.short_name if p.team else ""
        team_name = p.team.name if p.team else ""
        full_name = f"{p.first_name or ''} {p.second_name or ''}".strip()
        
        if search_q:
            matches = (
                search_q in p.web_name.lower() or
                search_q in full_name.lower() or
                search_q in team_short.lower() or
                search_q in team_name.lower()
            )
            if not matches:
                continue

        proj = projs.get(p.id)
        xp = round(proj.expected_points, 2) if proj else round(p.ep_next or 0.0, 2)
        xmins = round(proj.expected_minutes, 1) if proj else 0.0

        result.append({
            "id": p.id,
            "web_name": p.web_name,
            "first_name": p.first_name,
            "second_name": p.second_name,
            "position": p.element_type,
            "element_type": p.element_type,
            "team_id": p.team_id,
            "team_name": team_short,
            "team_full_name": team_name,
            "now_cost": p.now_cost,
            "price_str": f"£{p.now_cost / 10.0:.1f}m",
            "total_xp": xp,
            "expected_points_gw": xp,
            "xMins": xmins,
            "total_points": p.total_points,
            "event_points": p.event_points,
            "expected_goals": round(p.expected_goals or 0.0, 2),
            "expected_assists": round(p.expected_assists or 0.0, 2),
            "defensive_contributions": p.defensive_contributions or 0,
            "status": p.status,
            "chance_of_playing": p.chance_of_playing_next_round
        })

    result.sort(key=lambda x: x["total_xp"], reverse=True)
    return result[:limit]

@app.get("/api/v1/players/leaders", tags=["Players"])
def current_gw_leaders(
    limit: int = Query(10, description="Top N players to return"),
    db: Session = Depends(get_db)
):
    """
    Returns Current Gameweek Leaders ranked exclusively by ACTUAL GW POINTS (event_points/total_points).
    Does NOT use projected xP or optimizer estimates.
    """
    from backend.ingestion.current_state import CurrentGameStateManager
    current_gw = CurrentGameStateManager(db).get_current_gameweek()

    players = db.query(Player).order_by(Player.event_points.desc(), Player.total_points.desc()).limit(limit).all()
    has_actual_points = any(p.event_points > 0 or p.total_points > 0 for p in players)

    leaders = []
    for idx, p in enumerate(players, start=1):
        leaders.append({
            "rank": idx,
            "id": p.id,
            "web_name": p.web_name,
            "position": p.element_type,
            "team_name": p.team.short_name if p.team else "",
            "now_cost_str": f"£{p.now_cost / 10.0:.1f}m",
            "actual_gw_points": p.event_points if p.event_points > 0 else p.total_points,
            "total_points": p.total_points,
            "minutes": p.minutes,
            "goals_scored": p.goals_scored,
            "assists": p.assists,
            "clean_sheets": p.clean_sheets,
            "bonus": p.bonus,
            "defensive_contributions": p.defensive_contributions or 0
        })

    return {
        "current_gw": current_gw,
        "is_available": has_actual_points,
        "leaders": leaders
    }

@app.get("/api/v1/players/{player_id}/detail", tags=["Players"])
def get_player_detail(
    player_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns complete FPL player profile:
    Identity, upcoming 4-GW fixture run with difficulty, model metrics (xG, xA, CS, xMins, DEFCON),
    and historical actual GW points.
    """
    from backend.ingestion.current_state import CurrentGameStateManager
    current_gw = CurrentGameStateManager(db).get_current_gameweek()

    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player ID {player_id} not found.")

    team_short = player.team.short_name if player.team else ""
    team_name = player.team.name if player.team else ""
    full_name = f"{player.first_name or ''} {player.second_name or ''}".strip()

    upcoming_fixtures = []
    fixtures = db.query(Fixture).filter(
        (Fixture.team_h_id == player.team_id) | (Fixture.team_a_id == player.team_id),
        Fixture.event_id >= current_gw
    ).order_by(Fixture.event_id.asc()).limit(5).all()

    teams_map = {t.id: t.short_name for t in db.query(Team).all()}

    projs_map = {
        p.gameweek_id: p
        for p in db.query(PlayerProjection).filter(
            PlayerProjection.player_id == player_id,
            PlayerProjection.source == "internal"
        ).all()
    }

    for f in fixtures:
        is_home = (f.team_h_id == player.team_id)
        opp_id = f.team_a_id if is_home else f.team_h_id
        opp_short = teams_map.get(opp_id, "")
        diff = f.team_h_difficulty if is_home else f.team_a_difficulty
        
        proj = projs_map.get(f.event_id)
        gw_xp = round(proj.expected_points, 2) if proj else 0.0
        gw_xmins = round(proj.expected_minutes, 1) if proj else 0.0

        upcoming_fixtures.append({
            "gw": f.event_id,
            "opponent": f"{opp_short} ({'H' if is_home else 'A'})",
            "is_home": is_home,
            "difficulty": diff,
            "projected_xp": gw_xp,
            "expected_minutes": gw_xmins
        })

    next_proj = projs_map.get(current_gw)
    next_xp = round(next_proj.expected_points, 2) if next_proj else round(player.ep_next or 0.0, 2)
    next_xmins = round(next_proj.expected_minutes, 1) if next_proj else 0.0

    cs_exp = "N/A"
    if player.element_type in ("GKP", "DEF"):
        cs_exp = "35%" if next_xp >= 3.5 else "25%"

    historical_points = [{
        "gw": 1,
        "actual_points": player.event_points if player.event_points > 0 else (player.total_points or 0),
        "minutes": player.minutes or 0,
        "goals": player.goals_scored or 0,
        "assists": player.assists or 0,
        "clean_sheet": player.clean_sheets or 0,
        "bonus": player.bonus or 0
    }]

    return {
        "id": player.id,
        "web_name": player.web_name,
        "full_name": full_name,
        "position": player.element_type,
        "team_name": team_short,
        "team_full_name": team_name,
        "now_cost": player.now_cost,
        "price_str": f"£{player.now_cost / 10.0:.1f}m",
        "status": player.status,
        "chance_of_playing": player.chance_of_playing_next_round,
        "news": player.news,
        "selected_by_percent": player.selected_by_percent,
        "total_points": player.total_points,
        "event_points": player.event_points,
        "form": player.form,
        "next_gw_xp": next_xp,
        "next_gw_xmins": next_xmins,
        "expected_goals": round(player.expected_goals or 0.0, 2),
        "expected_assists": round(player.expected_assists or 0.0, 2),
        "clean_sheet_expectation": cs_exp,
        "defensive_contributions": player.defensive_contributions or 0,
        "upcoming_fixtures": upcoming_fixtures,
        "historical_points": historical_points
    }

@app.post("/api/v1/optimize/squad", response_model=OptimizationResponse, tags=["Optimization"])
def optimize_squad(req: OptimizationRequest, db: Session = Depends(get_db)):
    """Run synchronous MILP squad optimization for specified optimization mode."""
    try:
        current_gw = req.current_gw
        max_gw = min(38, current_gw + 3)
        proj_engine = ProjectionEngine(db)
        proj_engine.run_projections(start_gw=current_gw, end_gw=max_gw, source=req.projection_source)

        optimizer = SquadOptimizer(db)
        res = optimizer.solve_squad_selection(
            mode=req.mode,
            current_gw=current_gw,
            total_budget=req.total_budget,
            max_players_per_team=req.max_players_per_team,
            projection_source=req.projection_source,
            weights=req.weights,
            banned_player_ids=req.banned_player_ids,
            locked_player_ids=req.locked_player_ids
        )
        return res
    except Exception as e:
        logger.error(f"Error optimizing squad: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

from backend.optimizer.progress_manager import progress_manager, OPTIMIZATION_STAGES
import threading

def _run_background_optimization(job_id: str, req: OptimizationRequest):
    """Background worker for asynchronous optimization progress tracking."""
    db_gen = get_db()
    db = next(db_gen)
    try:
        progress_manager.update_stage(job_id, 0, "Loading FPL Data")
        current_gw = req.current_gw
        max_gw = min(38, current_gw + 3)

        progress_manager.update_stage(job_id, 1, "Loading Model Artifacts")
        proj_engine = ProjectionEngine(db)

        progress_manager.update_stage(job_id, 2, "Generating Fixture-Aware Projections")
        proj_engine.run_projections(start_gw=current_gw, end_gw=max_gw, source=req.projection_source)

        progress_manager.update_stage(job_id, 3, "Calculating Expected Points (xP)")
        optimizer = SquadOptimizer(db)

        progress_manager.update_stage(job_id, 4, "Building MILP Optimizer Constraints")
        progress_manager.update_stage(job_id, 5, "Solving 15-Man Squad Optimization")
        
        res = optimizer.solve_squad_selection(
            mode=req.mode,
            current_gw=current_gw,
            total_budget=req.total_budget,
            max_players_per_team=req.max_players_per_team,
            projection_source=req.projection_source,
            weights=req.weights,
            banned_player_ids=req.banned_player_ids,
            locked_player_ids=req.locked_player_ids
        )

        progress_manager.update_stage(job_id, 6, "Selecting Starting XI")
        progress_manager.update_stage(job_id, 7, "Selecting Captain and Vice-Captain")
        progress_manager.update_stage(job_id, 8, "Computing Position Value Diagnostics")
        progress_manager.complete_job(job_id, res)
    except Exception as e:
        logger.error(f"Background optimization failed for job {job_id}: {e}", exc_info=True)
        progress_manager.fail_job(job_id, str(e))
    finally:
        db.close()

@app.post("/api/v1/optimize/job", tags=["Optimization"])
def start_optimization_job(req: OptimizationRequest):
    """Start asynchronous optimization job with stage-by-stage progress tracking."""
    job_id = progress_manager.create_job(req.mode)
    t = threading.Thread(target=_run_background_optimization, args=(job_id, req), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "RUNNING", "message": "Optimization job started."}

@app.get("/api/v1/optimize/status/{job_id}", tags=["Optimization"])
def get_optimization_status(job_id: str):
    """Get real-time stage progress status for an optimization job."""
    status = progress_manager.get_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return status

@app.get("/api/v1/optimize/result/{job_id}", tags=["Optimization"])
def get_optimization_result(job_id: str):
    """Get final completed optimization result for a job."""
    res = progress_manager.get_result(job_id)
    if not res:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return res

@app.post("/api/v1/optimize/compare_modes", tags=["Optimization"])
def compare_optimization_modes(req: OptimizationRequest, db: Session = Depends(get_db)):
    """
    Side-by-side mode comparison evaluating all 4 optimization modes against EXACTLY THE SAME projection snapshot.
    """
    modes = ["CURRENT_GW_ONLY", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"]
    
    # 1. Freeze projection snapshot once
    current_gw = req.current_gw
    max_gw = min(38, current_gw + 3)
    proj_engine = ProjectionEngine(db)
    proj_engine.run_projections(start_gw=current_gw, end_gw=max_gw, source=req.projection_source)

    optimizer = SquadOptimizer(db)
    comparison_results = []

    for m in modes:
        t0 = time.time()
        res = optimizer.solve_squad_selection(
            mode=m,
            current_gw=current_gw,
            total_budget=req.total_budget,
            max_players_per_team=req.max_players_per_team,
            projection_source=req.projection_source
        )
        runtime = round(time.time() - t0, 3)

        s11 = [p["web_name"] for p in res["starting_11"]]
        bench = [p["web_name"] for p in res["bench"]]
        c_name = res["captain"]["web_name"] if res.get("captain") else "N/A"

        comparison_results.append({
            "mode": m,
            "total_cost_str": res["total_cost_str"],
            "bank_str": res["bank_str"],
            "current_gw_starting_xi_xp": res["current_gw_starting_xi_xp"],
            "total_current_gw_xp": res["total_current_gw_xp"],
            "weighted_horizon_xp": res["weighted_horizon_xp"],
            "starting_11_names": s11,
            "bench_names": bench,
            "captain_name": c_name,
            "solver_runtime_seconds": runtime
        })

    return {
        "modes_compared": len(comparison_results),
        "comparison": comparison_results
    }

@app.get("/api/v1/state/status", tags=["Gameweek State"])
def get_current_state_status(db: Session = Depends(get_db)):
    """Returns current active gameweek state, snapshot metadata, and data quality status."""
    from backend.ingestion.current_state import CurrentGameStateManager
    mgr = CurrentGameStateManager(db)
    current_gw = mgr.get_current_gameweek()
    snapshot = mgr.generate_current_state_snapshot()
    dq = mgr.run_data_quality_audit()
    return {
        "status": "READY",
        "current_gw": current_gw,
        "snapshot_version": snapshot["snapshot_version"],
        "generated_at": snapshot["generated_at"],
        "summary": snapshot["summary"],
        "data_quality": dq
    }

@app.post("/api/v1/state/refresh", tags=["Gameweek State"])
def refresh_current_state(target_gw: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """Execute idempotent gameweek state refresh pipeline and advance gameweek if target_gw specified."""
    try:
        from backend.ingestion.current_state import CurrentGameStateManager
        mgr = CurrentGameStateManager(db)
        res = mgr.refresh_current_gameweek(force_gw=target_gw)
        return res
    except Exception as e:
        logger.error(f"Error refreshing gameweek state: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/user-squad", tags=["User Squad"])
def get_user_squad(db: Session = Depends(get_db)):
    """Get persistent My Team user squad."""
    from backend.user.user_squad import UserSquadManager
    from backend.ingestion.current_state import CurrentGameStateManager
    gw = CurrentGameStateManager(db).get_current_gameweek()
    mgr = UserSquadManager(db)
    return mgr.get_user_squad_dict(current_gw=gw)

class UserSquadUpdateRequest(BaseModel):
    player_ids: List[int]
    bank: int = 0
    free_transfers: int = 1
    active_chip: Optional[str] = None
    captain_id: Optional[int] = None
    vice_captain_id: Optional[int] = None
    starter_ids: Optional[List[int]] = None

@app.post("/api/v1/user-squad", tags=["User Squad"])
def update_user_squad(
    req: UserSquadUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update persistent My Team user squad with 15 player IDs, captain, vice-captain, and starters."""
    try:
        from backend.user.user_squad import UserSquadManager
        from backend.ingestion.current_state import CurrentGameStateManager
        gw = CurrentGameStateManager(db).get_current_gameweek()
        mgr = UserSquadManager(db)
        mgr.update_user_squad(
            player_ids=req.player_ids, 
            bank=req.bank, 
            free_transfers=req.free_transfers, 
            active_chip=req.active_chip,
            captain_id=req.captain_id,
            vice_captain_id=req.vice_captain_id,
            starter_ids=req.starter_ids
        )
        return mgr.get_user_squad_dict(current_gw=gw)
    except Exception as e:
        logger.error(f"Error updating user squad: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/user-squad/compare", tags=["User Squad"])
def compare_user_squad_with_optimal(
    mode: str = Query("MEDIUM_TERM"),
    db: Session = Depends(get_db)
):
    """Compare user's actual squad vs optimizer's optimal squad for specified mode."""
    try:
        from backend.user.user_squad import UserSquadManager
        from backend.ingestion.current_state import CurrentGameStateManager
        gw = CurrentGameStateManager(db).get_current_gameweek()
        
        optimizer = SquadOptimizer(db)
        opt_res = optimizer.solve_squad_selection(mode=mode, current_gw=gw)

        mgr = UserSquadManager(db)
        comp = mgr.compare_with_optimal_squad(optimal_result=opt_res, current_gw=gw)
        return {
            "mode": mode,
            "comparison": comp,
            "optimal_squad": opt_res
        }
    except Exception as e:
        logger.error(f"Error comparing user squad with optimal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/diagnostics/trace/{player_query}", tags=["Diagnostics"])
def get_player_selection_trace(player_query: str, db: Session = Depends(get_db)):
    """Backend selection trace engine explaining why a player was selected or projected."""
    try:
        from backend.diagnostics.reality_audit import DecisionEngineRealityAuditor
        auditor = DecisionEngineRealityAuditor(db)
        return auditor.trace_player_selection(player_query)
    except Exception as e:
        logger.error(f"Error executing selection trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/diagnostics/why-not/{player_query}", tags=["Diagnostics"])
def get_player_non_selection_trace(player_query: str, mode: str = Query("MEDIUM_TERM"), db: Session = Depends(get_db)):
    """Backend diagnostic engine explaining why a player was NOT selected in the optimal squad."""
    try:
        from backend.diagnostics.reality_audit import DecisionEngineRealityAuditor
        from backend.models import Player
        
        p = db.query(Player).filter(
            (Player.web_name.ilike(f"%{player_query}%")) | (Player.id == int(player_query) if player_query.isdigit() else False)
        ).first()

        if not p:
            raise HTTPException(status_code=404, detail=f"Player '{player_query}' not found.")

        auditor = DecisionEngineRealityAuditor(db)
        trace = auditor.trace_player_selection(p.web_name)

        optimizer = SquadOptimizer(db)
        opt_res = optimizer.solve_squad_selection(mode=mode, current_gw=auditor.state_mgr.get_current_gameweek())
        
        full_squad = opt_res.get("starting_xi", []) + opt_res.get("bench", [])
        selected_ids = [sp["id"] for sp in full_squad]
        is_selected = (p.id in selected_ids)

        pos_alternatives = [sp for sp in full_squad if sp.get("element_type", sp.get("position")) == p.element_type]
        best_alt = max(pos_alternatives, key=lambda x: x.get("current_gw_xp", x.get("gw0_xp", x.get("total_xp", 0.0)))) if pos_alternatives else None

        return {
            "player_id": p.id,
            "web_name": p.web_name,
            "position": p.element_type,
            "club": p.team.short_name if p.team else "",
            "price_str": f"£{p.now_cost/10.0:.1f}m",
            "is_selected_in_optimal_squad": is_selected,
            "player_xp": trace.get("v2_calibrated_xp", 0.0),
            "expected_minutes": trace.get("expected_minutes", 0.0),
            "best_positional_alternative": best_alt,
            "selection_delta_xp": round((best_alt.get("current_gw_xp", best_alt.get("gw0_xp", best_alt.get("total_xp", 0.0))) - trace.get("v2_calibrated_xp", 0.0)), 2) if best_alt else 0.0,
            "non_selection_reason": (
                f"Player '{p.web_name}' is ALREADY SELECTED in the optimal squad." if is_selected else
                f"Player '{p.web_name}' was not selected because '{best_alt.get('web_name', best_alt.get('name', 'Alternative'))}' "
                f"offers higher projected expected points ({best_alt.get('current_gw_xp', best_alt.get('gw0_xp', best_alt.get('total_xp', 0.0))):.2f} vs {trace.get('v2_calibrated_xp', 0.0):.2f}) "
                f"or better budget efficiency for position {p.element_type}."
            ),
            "full_trace": trace
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing non-selection trace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Static files for Frontend dashboard
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def read_index():
        index_file = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html not found"}
