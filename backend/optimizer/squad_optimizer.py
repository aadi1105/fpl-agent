import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ortools.linear_solver import pywraplp

from backend.config import settings
from backend.models import Player, Team, PlayerProjection, ElementType

logger = logging.getLogger("squad_optimizer")
logging.basicConfig(level=logging.INFO)

class SquadOptimizer:
    def __init__(self, db: Session):
        self.db = db

    def solve_squad_selection(
        self,
        mode: str = "CURRENT_GW_PLUS_3",
        current_gw: int = 1,
        total_budget: int = settings.TOTAL_BUDGET,
        max_players_per_team: int = settings.MAX_PLAYERS_PER_TEAM,
        projection_source: str = "internal",
        weights: Optional[List[float]] = None,
        banned_player_ids: Optional[List[int]] = None,
        locked_player_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Two-Step Optimization:
        Step 1 (Squad Selection): Select 15-man squad maximizing Weighted 4-GW outlook.
        Step 2 (Lineup Selection): Select 11 starting players for CURRENT GAMEWEEK maximizing GW0 xP.
        """
        banned_player_ids = banned_player_ids or []
        locked_player_ids = locked_player_ids or []

        # Determine 4-GW horizon: [GW0, GW1, GW2, GW3]
        horizon_gws = [current_gw + k for k in range(4) if (current_gw + k) <= 38]
        if not horizon_gws:
            horizon_gws = [current_gw]

        # Determine horizon weights based on mode
        if mode == "MAXIMUM_SQUAD":
            gw_weights = [0.25, 0.25, 0.25, 0.25][:len(horizon_gws)]
        elif weights and len(weights) == len(horizon_gws):
            gw_weights = weights
        else:
            gw_weights = settings.DEFAULT_HORIZON_WEIGHTS[:len(horizon_gws)]

        # Normalize weights to sum to 1.0
        w_sum = sum(gw_weights)
        gw_weights = [round(w / w_sum, 3) for w in gw_weights]

        players = self.db.query(Player).all()
        teams = self.db.query(Team).all()

        # Fetch projections for horizon
        projections = self.db.query(PlayerProjection).filter(
            PlayerProjection.gameweek_id.in_(horizon_gws),
            PlayerProjection.source == projection_source
        ).all()

        # Map player per-GW expected points
        # player_gw_xp[pid][gw] = xP
        player_gw_xp: Dict[int, Dict[int, float]] = {p.id: {} for p in players}
        for proj in projections:
            if proj.player_id in player_gw_xp:
                player_gw_xp[proj.player_id][proj.gameweek_id] = proj.expected_points

        # Calculate per-player weighted xP across 4-GW horizon
        player_weighted_xp: Dict[int, float] = {}
        player_gw0_xp: Dict[int, float] = {}

        for p in players:
            pid = p.id
            gw0_xp = player_gw_xp[pid].get(current_gw, 0.0)
            player_gw0_xp[pid] = gw0_xp

            weighted = 0.0
            for idx, gw in enumerate(horizon_gws):
                xp_val = player_gw_xp[pid].get(gw, 0.0)
                weighted += xp_val * gw_weights[idx]
            
            player_weighted_xp[pid] = round(weighted, 2)

        # -------------------------------------------------------------
        # STEP 1: SQUAD SELECTION (15 Players)
        # -------------------------------------------------------------
        solver1 = pywraplp.Solver.CreateSolver('CBC')
        if not solver1:
            solver1 = pywraplp.Solver.CreateSolver('SCIP')
        if not solver1:
            raise RuntimeError("OR-Tools solver CBC/SCIP not available.")

        x = {p.id: solver1.BoolVar(f"x_{p.id}") for p in players}

        for pid in banned_player_ids:
            if pid in x: solver1.Add(x[pid] == 0)
        for pid in locked_player_ids:
            if pid in x: solver1.Add(x[pid] == 1)

        # 1. Total Squad Size = 15
        solver1.Add(solver1.Sum([x[p.id] for p in players]) == settings.SQUAD_SIZE)

        # 2. Total Budget <= total_budget (in tenths, e.g. 1000 = £100.0m)
        solver1.Add(solver1.Sum([p.now_cost * x[p.id] for p in players]) <= total_budget)

        # 3. Position counts (2 GKP, 5 DEF, 5 MID, 3 FWD)
        for pos, count in settings.POSITION_COUNTS.items():
            pos_players = [p for p in players if p.element_type == pos]
            solver1.Add(solver1.Sum([x[p.id] for p in pos_players]) == count)

        # 4. Max 3 players per club
        for team in teams:
            team_players = [p for p in players if p.team_id == team.id]
            solver1.Add(solver1.Sum([x[p.id] for p in team_players]) <= max_players_per_team)

        # Objective Step 1: Maximize Weighted Squad xP
        obj1 = solver1.Objective()
        for p in players:
            pid = p.id
            w_xp = player_weighted_xp.get(pid, 0.0)
            
            if mode == "STRONG_XI_DUMP_BENCH":
                # Add penalty to bench expenditure so budget is concentrated on top starting XI
                cost_penalty = 0.005 * p.now_cost
                obj1.SetCoefficient(x[pid], w_xp - cost_penalty)
            else:
                obj1.SetCoefficient(x[pid], w_xp)

        obj1.SetMaximization()
        status1 = solver1.Solve()

        if status1 not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            raise RuntimeError(f"Squad optimization failed with solver status code: {status1}")

        selected_squad = [p for p in players if x[p.id].solution_value() > 0.5]
        selected_squad_ids = set(p.id for p in selected_squad)

        # -------------------------------------------------------------
        # STEP 2: CURRENT GAMEWEEK STARTING XI SELECTION (11 Players)
        # -------------------------------------------------------------
        solver2 = pywraplp.Solver.CreateSolver('CBC')
        if not solver2: solver2 = pywraplp.Solver.CreateSolver('SCIP')

        s = {p.id: solver2.BoolVar(f"s_{p.id}") for p in selected_squad}

        # 1. Starting XI count = 11
        solver2.Add(solver2.Sum([s[p.id] for p in selected_squad]) == 11)

        # 2. Formation limits for Starting XI
        for pos, (min_start, max_start) in settings.STARTING_FORMATION_LIMITS.items():
            pos_squad = [p for p in selected_squad if p.element_type == pos]
            solver2.Add(solver2.Sum([s[p.id] for p in pos_squad]) >= min_start)
            solver2.Add(solver2.Sum([s[p.id] for p in pos_squad]) <= max_start)

        # Objective Step 2: Maximize CURRENT GAMEWEEK (GW0) xP ONLY
        obj2 = solver2.Objective()
        for p in selected_squad:
            gw0_val = player_gw0_xp.get(p.id, 0.0)
            obj2.SetCoefficient(s[p.id], gw0_val)

        obj2.SetMaximization()
        status2 = solver2.Solve()

        if status2 not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            raise RuntimeError(f"Starting XI optimization failed with solver status code: {status2}")

        starters = [p for p in selected_squad if s[p.id].solution_value() > 0.5]
        bench_players = [p for p in selected_squad if s[p.id].solution_value() <= 0.5]

        # -------------------------------------------------------------
        # STEP 3: CAPTAIN & VICE-CAPTAIN SELECTION
        # -------------------------------------------------------------
        # Sort starters by GW0 xP descending
        starters.sort(key=lambda p: player_gw0_xp.get(p.id, 0.0), reverse=True)
        captain_player = starters[0] if starters else None
        vice_captain_player = starters[1] if len(starters) > 1 else None

        # Build output player dicts
        starting_11_dicts = []
        bench_dicts = []
        total_cost = 0
        current_gw_starting_xi_xp = 0.0
        weighted_squad_xp = 0.0

        for p in selected_squad:
            total_cost += p.now_cost
            pid = p.id
            is_starter = (p in starters)
            is_cap = (p == captain_player)
            is_vc = (p == vice_captain_player)

            gw0 = round(player_gw0_xp.get(pid, 0.0), 2)
            gw1 = round(player_gw_xp[pid].get(horizon_gws[1] if len(horizon_gws) > 1 else current_gw, 0.0), 2)
            gw2 = round(player_gw_xp[pid].get(horizon_gws[2] if len(horizon_gws) > 2 else current_gw, 0.0), 2)
            gw3 = round(player_gw_xp[pid].get(horizon_gws[3] if len(horizon_gws) > 3 else current_gw, 0.0), 2)
            w_xp = round(player_weighted_xp.get(pid, 0.0), 2)

            weighted_squad_xp += w_xp

            p_dict = {
                "id": p.id,
                "web_name": p.web_name,
                "first_name": p.first_name,
                "second_name": p.second_name,
                "element_type": p.element_type,
                "team_id": p.team_id,
                "team_name": p.team.short_name if p.team else "",
                "now_cost": p.now_cost,
                "now_cost_str": f"£{p.now_cost / 10.0:.1f}m",
                "gw0_xp": gw0,
                "gw1_xp": gw1,
                "gw2_xp": gw2,
                "gw3_xp": gw3,
                "weighted_xp": w_xp,
                "expected_points_total": w_xp,
                "expected_points_per_gw": gw0,
                "expected_points": gw0,
                "is_starter": is_starter,
                "is_captain": is_cap,
                "is_vice_captain": is_vc
            }

            if is_starter:
                current_gw_starting_xi_xp += gw0
                starting_11_dicts.append(p_dict)
            else:
                bench_dicts.append(p_dict)

        captain_dict = next((d for d in starting_11_dicts if d["is_captain"]), None)
        vice_captain_dict = next((d for d in starting_11_dicts if d["is_vice_captain"]), None)

        captain_extra = captain_dict["gw0_xp"] if captain_dict else 0.0
        total_current_gw_xp = current_gw_starting_xi_xp + captain_extra

        # Sort starting 11 by position order (GKP, DEF, MID, FWD)
        pos_order = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
        starting_11_dicts.sort(key=lambda d: (pos_order.get(d["element_type"], 5), -d["gw0_xp"]))
        bench_dicts.sort(key=lambda d: (pos_order.get(d["element_type"], 5), -d["gw0_xp"]))

        # Build Explanations
        explanations = []
        if captain_dict:
            explanations.append(f"Captain Pick: {captain_dict['web_name']} ({captain_dict['gw0_xp']} GW{current_gw} xP) selected for highest current GW expected return.")
        if mode == "STRONG_XI_DUMP_BENCH":
            explanations.append("Strong XI / Dump Bench mode concentrated budget into top starting XI while selecting minimal bench enablers.")
        else:
            explanations.append(f"Current GW + 3 Mode weighted GW{current_gw} at {gw_weights[0]*100:.0f}% while evaluating upcoming fixtures across 4 GWs.")

        anomalies = []
        if total_cost < 950:
            anomalies.append(f"Unused budget alert: £{(total_budget - total_cost)/10.0:.1f}m unspent.")

        return {
            "model_version": settings.MODEL_VERSION,
            "optimization_mode": mode,
            "current_gw": current_gw,
            "horizon_weights": gw_weights,
            "total_budget": total_budget,
            "total_cost": total_cost,
            "total_cost_str": f"£{total_cost / 10.0:.1f}m",
            "bank": total_budget - total_cost,
            "bank_str": f"£{(total_budget - total_cost) / 10.0:.1f}m",
            "current_gw_starting_xi_xp": round(current_gw_starting_xi_xp, 2),
            "captain_contribution_xp": round(captain_extra, 2),
            "total_current_gw_xp": round(total_current_gw_xp, 2),
            "weighted_horizon_xp": round(weighted_squad_xp, 2),
            "captain": captain_dict,
            "vice_captain": vice_captain_dict,
            "starting_11": starting_11_dicts,
            "bench": bench_dicts,
            "squad_count": len(starting_11_dicts) + len(bench_dicts),
            "anomalies": anomalies,
            "explanations": explanations
        }
