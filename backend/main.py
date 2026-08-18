import os
import time
import logging
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

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

@app.get("/api/v1/projections/diagnostics", tags=["Projections"])
def get_projection_diagnostics(
    target_gw: int = Query(1, description="Gameweek to inspect"),
    position: Optional[str] = Query(None, description="Filter by position (GKP, DEF, MID, FWD)"),
    sort_by: str = Query("weighted_xp", description="Sort field: weighted_xp, total_xp, xp_per_m, price, xMins"),
    limit: int = Query(100, description="Max players to return"),
    db: Session = Depends(get_db)
):
    """
    Returns full component breakdown and 4-GW fixture outlook for every player for arithmetic validation and auditing.
    """
    engine = ProjectionEngine(db)
    query = db.query(Player)
    if position:
        query = query.filter(Player.element_type == position.upper())

    players = query.all()
    teams_map = {t.id: t for t in db.query(Team).all()}
    horizon_gws = [target_gw + k for k in range(4) if (target_gw + k) <= 38]
    weights = settings.DEFAULT_HORIZON_WEIGHTS[:len(horizon_gws)]
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
            weighted_xp += bd.get("total_xp", 0.0) * weights[idx]

        gw0_bd = gw_breakdowns.get(target_gw, {})
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
            "total_xp": gw0_bd.get("total_xp", 0.0),
            "xp_per_m": gw0_bd.get("xp_per_m", 0.0),
            "weighted_xp": round(weighted_xp, 2),
            **gw_opponents,
            **gw_xps
        }

        # Verify strict arithmetic equality for GW0
        component_sum = round(
            entry["appearance_xp"] + entry["goals_xp"] + entry["assists_xp"] +
            entry["cs_xp"] + entry["defcon_xp"] + entry["saves_xp"] +
            entry["bonus_xp"] + entry["cards_xp"], 2
        )
        entry["arithmetic_valid"] = abs(entry["total_xp"] - max(0.0, component_sum)) < 0.05
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

    team_fixture_map = {}
    for f in fixtures:
        if f.team_h_id not in team_fixture_map: team_fixture_map[f.team_h_id] = []
        team_fixture_map[f.team_h_id].append((f, True, teams_map.get(f.team_a_id)))

        if f.team_a_id not in team_fixture_map: team_fixture_map[f.team_a_id] = []
        team_fixture_map[f.team_a_id].append((f, False, teams_map.get(f.team_h_id)))

    benchmark_list = []
    for player in players:
        p_fixtures = team_fixture_map.get(player.team_id, [])
        if p_fixtures:
            f, is_home, opp_team = p_fixtures[0]
            bd = engine.calculate_player_xp_breakdown(player, f, is_home, opp_team)
            bd["id"] = player.id
            bd["team_name"] = player.team.short_name if player.team else ""
            benchmark_list.append(bd)

    benchmark_list.sort(key=lambda x: x["total_xp"], reverse=True)
    return {
        "benchmark_count": len(benchmark_list),
        "rankings": benchmark_list
    }

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
            "expected_goals": p.expected_goals,
            "expected_assists": p.expected_assists,
            "defensive_contributions": p.defensive_contributions
        })

    # Sort by expected points descending
    result.sort(key=lambda x: x["expected_points_gw"], reverse=True)
    return result[:limit]

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
    modes = ["CURRENT_GW_PLUS_3", "STRONG_XI_DUMP_BENCH", "BALANCED_BENCH", "MAXIMUM_SQUAD"]
    
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
