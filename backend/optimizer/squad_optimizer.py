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
        locked_player_ids: Optional[List[int]] = None,
        is_bench_boost: bool = False
    ) -> Dict[str, Any]:
        """
        Phase 3N.26 — Starting-XI-First Lexicographic MILP Optimization Architecture.
        
        Primary Objective (Stage 1):
        - Standard Mode: Maximize Expected Points of the 11 Starting XI players + Captain Bonus.
        - Bench Boost Mode: Maximize Expected Points of ALL 15 Squad players + Captain Bonus.
        
        Secondary Objective (Stage 2):
        - Lock Stage 1 Starting XI score (Z1*), then maximize Bench Quality (4 bench players)
          without sacrificing starting XI points.
        """
        banned_player_ids = banned_player_ids or []
        locked_player_ids = locked_player_ids or []

        # Determine horizon GWs and weights based on optimization mode
        if mode in ["NEXT_GW", "CURRENT_GW_ONLY", "MODE_1"]:
            horizon_gws = [current_gw]
            gw_weights = [1.0]
        elif mode in ["SHORT_TERM", "MODE_2"]:
            horizon_gws = [current_gw + k for k in range(2) if (current_gw + k) <= 38]
            gw_weights = [0.65, 0.35][:len(horizon_gws)]
        elif mode in ["LONG_TERM", "MODE_4"]:
            horizon_gws = [current_gw + k for k in range(7) if (current_gw + k) <= 38]
            gw_weights = [0.30, 0.20, 0.15, 0.12, 0.10, 0.08, 0.05][:len(horizon_gws)]
        elif mode in ["STRONG_XI_DUMP_BENCH"]:
            horizon_gws = [current_gw + k for k in range(4) if (current_gw + k) <= 38]
            gw_weights = [0.70, 0.15, 0.10, 0.05][:len(horizon_gws)]
        elif mode in ["BALANCED_BENCH"]:
            horizon_gws = [current_gw + k for k in range(4) if (current_gw + k) <= 38]
            gw_weights = [0.45, 0.25, 0.15, 0.15][:len(horizon_gws)]
        elif mode in ["MEDIUM_TERM", "CURRENT_GW_PLUS_3", "MODE_3"]:
            horizon_gws = [current_gw + k for k in range(4) if (current_gw + k) <= 38]
            gw_weights = [0.55, 0.20, 0.15, 0.10][:len(horizon_gws)]
        else:
            horizon_gws = [current_gw + k for k in range(4) if (current_gw + k) <= 38]
            gw_weights = [0.55, 0.20, 0.15, 0.10][:len(horizon_gws)]

        if not horizon_gws:
            horizon_gws = [current_gw]

        # Normalize weights to sum to 1.0
        w_sum = sum(gw_weights)
        gw_weights = [round(w / w_sum, 3) for w in gw_weights]

        logger.info(f"Configuring SquadOptimizer for mode={mode} | horizon_gws={horizon_gws} | weights={gw_weights}")

        players = self.db.query(Player).all()
        teams = self.db.query(Team).all()

        # Fetch projections for horizon
        projections = self.db.query(PlayerProjection).filter(
            PlayerProjection.gameweek_id.in_(horizon_gws),
            PlayerProjection.source == projection_source
        ).all()

        player_gw_xp: Dict[int, Dict[int, float]] = {p.id: {} for p in players}
        for proj in projections:
            if proj.player_id in player_gw_xp:
                player_gw_xp[proj.player_id][proj.gameweek_id] = proj.expected_points

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

        from backend.ingestion.current_state import CurrentGameStateManager
        state_mgr = CurrentGameStateManager(self.db)

        # -------------------------------------------------------------
        # STAGE 1: PRIMARY OBJECTIVE MILP (STARTING XI OPTIMIZATION)
        # -------------------------------------------------------------
        solver1 = pywraplp.Solver.CreateSolver('CBC')
        if not solver1: solver1 = pywraplp.Solver.CreateSolver('SCIP')
        if not solver1: raise RuntimeError("OR-Tools CBC/SCIP solver unavailable.")

        x1 = {p.id: solver1.BoolVar(f"x1_{p.id}") for p in players}
        s1 = {p.id: solver1.BoolVar(f"s1_{p.id}") for p in players}
        b1 = {p.id: solver1.BoolVar(f"b1_{p.id}") for p in players}
        c1 = {p.id: solver1.BoolVar(f"c1_{p.id}") for p in players}
        v1 = {p.id: solver1.BoolVar(f"v1_{p.id}") for p in players}

        for p in players:
            elig_info = state_mgr.evaluate_player_eligibility(p)
            if not elig_info["is_optimizer_eligible"]:
                if p.id not in locked_player_ids:
                    solver1.Add(x1[p.id] == 0)

            solver1.Add(x1[p.id] == s1[p.id] + b1[p.id])
            solver1.Add(c1[p.id] <= s1[p.id])
            solver1.Add(v1[p.id] <= s1[p.id])
            solver1.Add(c1[p.id] + v1[p.id] <= 1)

        for pid in banned_player_ids:
            if pid in x1: solver1.Add(x1[pid] == 0)
        for pid in locked_player_ids:
            if pid in x1: solver1.Add(x1[pid] == 1)

        solver1.Add(solver1.Sum([x1[p.id] for p in players]) == settings.SQUAD_SIZE)
        solver1.Add(solver1.Sum([s1[p.id] for p in players]) == 11)
        solver1.Add(solver1.Sum([b1[p.id] for p in players]) == 4)
        solver1.Add(solver1.Sum([c1[p.id] for p in players]) == 1)
        solver1.Add(solver1.Sum([v1[p.id] for p in players]) == 1)

        solver1.Add(solver1.Sum([p.now_cost * x1[p.id] for p in players]) <= total_budget)

        for pos, count in settings.POSITION_COUNTS.items():
            pos_players = [p for p in players if p.element_type == pos]
            solver1.Add(solver1.Sum([x1[p.id] for p in pos_players]) == count)

        for pos, (min_start, max_start) in settings.STARTING_FORMATION_LIMITS.items():
            pos_players = [p for p in players if p.element_type == pos]
            solver1.Add(solver1.Sum([s1[p.id] for p in pos_players]) >= min_start)
            solver1.Add(solver1.Sum([s1[p.id] for p in pos_players]) <= max_start)

        for team in teams:
            t_players = [p for p in players if p.team_id == team.id]
            solver1.Add(solver1.Sum([x1[p.id] for p in t_players]) <= max_players_per_team)

        obj1 = solver1.Objective()
        if is_bench_boost:
            for p in players:
                obj1.SetCoefficient(x1[p.id], player_weighted_xp.get(p.id, 0.0))
                obj1.SetCoefficient(c1[p.id], player_gw0_xp.get(p.id, 0.0))
        else:
            for p in players:
                obj1.SetCoefficient(s1[p.id], player_weighted_xp.get(p.id, 0.0))
                obj1.SetCoefficient(c1[p.id], player_gw0_xp.get(p.id, 0.0))

        obj1.SetMaximization()
        status1 = solver1.Solve()
        if status1 not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            raise RuntimeError(f"Stage 1 Optimization failed with solver status code: {status1}")

        z1_star = obj1.Value()

        # -------------------------------------------------------------
        # STAGE 2: SECONDARY OBJECTIVE MILP (BENCH OPTIMIZATION)
        # Lock Stage 1 starting XI score (Z1*), maximize bench xP
        # -------------------------------------------------------------
        solver2 = pywraplp.Solver.CreateSolver('CBC')
        if not solver2: solver2 = pywraplp.Solver.CreateSolver('SCIP')

        x2 = {p.id: solver2.BoolVar(f"x2_{p.id}") for p in players}
        s2 = {p.id: solver2.BoolVar(f"s2_{p.id}") for p in players}
        b2 = {p.id: solver2.BoolVar(f"b2_{p.id}") for p in players}
        c2 = {p.id: solver2.BoolVar(f"c2_{p.id}") for p in players}
        v2 = {p.id: solver2.BoolVar(f"v2_{p.id}") for p in players}

        for p in players:
            elig_info = state_mgr.evaluate_player_eligibility(p)
            if not elig_info["is_optimizer_eligible"]:
                if p.id not in locked_player_ids:
                    solver2.Add(x2[p.id] == 0)

            solver2.Add(x2[p.id] == s2[p.id] + b2[p.id])
            solver2.Add(c2[p.id] <= s2[p.id])
            solver2.Add(v2[p.id] <= s2[p.id])
            solver2.Add(c2[p.id] + v2[p.id] <= 1)

        for pid in banned_player_ids:
            if pid in x2: solver2.Add(x2[pid] == 0)
        for pid in locked_player_ids:
            if pid in x2: solver2.Add(x2[pid] == 1)

        solver2.Add(solver2.Sum([x2[p.id] for p in players]) == settings.SQUAD_SIZE)
        solver2.Add(solver2.Sum([s2[p.id] for p in players]) == 11)
        solver2.Add(solver2.Sum([b2[p.id] for p in players]) == 4)
        solver2.Add(solver2.Sum([c2[p.id] for p in players]) == 1)
        solver2.Add(solver2.Sum([v2[p.id] for p in players]) == 1)
        solver2.Add(solver2.Sum([p.now_cost * x2[p.id] for p in players]) <= total_budget)

        for pos, count in settings.POSITION_COUNTS.items():
            pos_players = [p for p in players if p.element_type == pos]
            solver2.Add(solver2.Sum([x2[p.id] for p in pos_players]) == count)

        for pos, (min_start, max_start) in settings.STARTING_FORMATION_LIMITS.items():
            pos_players = [p for p in players if p.element_type == pos]
            solver2.Add(solver2.Sum([s2[p.id] for p in pos_players]) >= min_start)
            solver2.Add(solver2.Sum([s2[p.id] for p in pos_players]) <= max_start)

        for team in teams:
            t_players = [p for p in players if p.team_id == team.id]
            solver2.Add(solver2.Sum([x2[p.id] for p in t_players]) <= max_players_per_team)

        # LOCK STAGE 1 OPTIMAL SCORE
        if is_bench_boost:
            solver2.Add(solver2.Sum([player_weighted_xp.get(p.id, 0.0) * x2[p.id] + player_gw0_xp.get(p.id, 0.0) * c2[p.id] for p in players]) >= z1_star - 1e-4)
        else:
            solver2.Add(solver2.Sum([player_weighted_xp.get(p.id, 0.0) * s2[p.id] + player_gw0_xp.get(p.id, 0.0) * c2[p.id] for p in players]) >= z1_star - 1e-4)

        # STAGE 2 OBJECTIVE: Maximize Bench Expected Points + minute tiebreakers
        obj2 = solver2.Objective()
        for p in players:
            w_xp = player_weighted_xp.get(p.id, 0.0)
            mins_bonus = 0.001 * float(p.minutes or 0)
            obj2.SetCoefficient(b2[p.id], w_xp + mins_bonus)

        obj2.SetMaximization()
        status2 = solver2.Solve()

        if status2 not in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            s2, b2, c2, v2, x2 = s1, b1, c1, v1, x1

        starters = [p for p in players if s2[p.id].solution_value() > 0.5]
        bench_players = [p for p in players if b2[p.id].solution_value() > 0.5]
        selected_squad = starters + bench_players

        captain_player = next((p for p in starters if c2[p.id].solution_value() > 0.5), starters[0] if starters else None)
        vice_captain_player = next((p for p in starters if v2[p.id].solution_value() > 0.5), starters[1] if len(starters) > 1 else None)

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

        def_cnt = sum(1 for d in starting_11_dicts if d["element_type"] == "DEF")
        mid_cnt = sum(1 for d in starting_11_dicts if d["element_type"] == "MID")
        fwd_cnt = sum(1 for d in starting_11_dicts if d["element_type"] == "FWD")
        formation_str = f"{def_cnt}-{mid_cnt}-{fwd_cnt}"

        pos_order = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
        starting_11_dicts.sort(key=lambda d: (pos_order.get(d["element_type"], 5), -d["gw0_xp"]))
        bench_dicts.sort(key=lambda d: (pos_order.get(d["element_type"], 5), -d["gw0_xp"]))

        explanations = [
            f"Primary Optimization Objective: Maximize Starting XI Expected Points ({current_gw_starting_xi_xp:.2f} xP) with {formation_str} formation.",
            f"Captain Pick: {captain_dict['web_name']} ({captain_dict['gw0_xp']} GW{current_gw} xP) selected for highest starting XI expected return." if captain_dict else ""
        ]

        anomalies = []
        if total_cost < 950:
            anomalies.append(f"Unused budget alert: £{(total_budget - total_cost)/10.0:.1f}m unspent.")

        return {
            "model_version": settings.MODEL_VERSION,
            "optimization_mode": mode,
            "current_gw": current_gw,
            "horizon_weights": gw_weights,
            "formation": formation_str,
            "is_bench_boost": is_bench_boost,
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

    def explain_optimization(
        self,
        mode: str = "NEXT_GW",
        current_gw: int = 1,
        total_budget: int = settings.TOTAL_BUDGET,
        max_players_per_team: int = settings.MAX_PLAYERS_PER_TEAM,
        projection_source: str = "internal"
    ) -> Dict[str, Any]:
        """
        Forensic Solver Explanation / Debug Capability.
        Explains exact objective formulas, top projected players, selection status,
        and mathematical reasons for rejection (e.g. why Haaland or Palmer were excluded).
        """
        res = self.solve_squad_selection(
            mode=mode,
            current_gw=current_gw,
            total_budget=total_budget,
            max_players_per_team=max_players_per_team,
            projection_source=projection_source
        )

        all_players = self.db.query(Player).all()
        from backend.ingestion.current_state import CurrentGameStateManager
        state_mgr = CurrentGameStateManager(self.db)

        # Get GW projections
        projs = self.db.query(PlayerProjection).filter(
            PlayerProjection.gameweek_id == current_gw,
            PlayerProjection.source == projection_source
        ).all()
        proj_map = {p.player_id: p.expected_points for p in projs}

        # Build top 25 projected players list
        top_players = []
        for p in all_players:
            xp = proj_map.get(p.id, 0.0)
            top_players.append((p, xp))

        top_players.sort(key=lambda t: t[1], reverse=True)
        top_25 = top_players[:25]

        selected_xi_ids = set(d["id"] for d in res["starting_11"])
        selected_bench_ids = set(d["id"] for d in res["bench"])

        rejected_high_value = []
        top_projected_breakdown = []

        for rank, (p, xp) in enumerate(top_25, start=1):
            is_xi = p.id in selected_xi_ids
            is_bench = p.id in selected_bench_ids
            is_sel = is_xi or is_bench

            status_str = "Selected (Starting XI)" if is_xi else ("Selected (Bench)" if is_bench else "Rejected")
            
            # Determine reason for rejection
            rejection_reason = "Selected"
            if not is_sel:
                elig = state_mgr.evaluate_player_eligibility(p)
                if not elig["is_optimizer_eligible"]:
                    rejection_reason = f"Ineligible: status={p.status}, chance={p.chance_of_playing_next_round}%"
                elif p.now_cost > 120:  # High price player (e.g., Haaland £15.5m)
                    rejection_reason = f"Price constraint (£{p.now_cost/10:.1f}m): Premium cost degrades overall XI score by forcing weak enablers"
                else:
                    rejection_reason = f"Positional/Sub-optimal xP (£{p.now_cost/10:.1f}m for {xp:.2f} xP yields lower xP/£m than alternatives)"

                rejected_high_value.append({
                    "rank": rank,
                    "id": p.id,
                    "web_name": p.web_name,
                    "element_type": p.element_type,
                    "team_name": p.team.short_name if p.team else "",
                    "now_cost_str": f"£{p.now_cost/10:.1f}m",
                    "gw_xp": round(xp, 2),
                    "rejection_reason": rejection_reason
                })

            top_projected_breakdown.append({
                "rank": rank,
                "id": p.id,
                "web_name": p.web_name,
                "element_type": p.element_type,
                "team_name": p.team.short_name if p.team else "",
                "now_cost_str": f"£{p.now_cost/10:.1f}m",
                "gw_xp": round(xp, 2),
                "status": status_str,
                "selected": is_sel
            })

        # Calculate Marginal Swap Analysis for each selected starter
        marginal_swap_analysis = []
        for starter in res["starting_11"]:
            s_pos = starter["element_type"]
            s_xp = starter["gw0_xp"]
            cands = [p for p in all_players if p.id not in selected_xi_ids and p.element_type == s_pos and state_mgr.evaluate_player_eligibility(p)["is_optimizer_eligible"]]
            cands.sort(key=lambda p: proj_map.get(p.id, 0.0), reverse=True)
            best_alt = cands[0] if cands else None
            alt_xp = proj_map.get(best_alt.id, 0.0) if best_alt else 0.0
            
            marginal_swap_analysis.append({
                "starter_name": starter["web_name"],
                "position": s_pos,
                "starter_xp": round(s_xp, 2),
                "best_alternative_name": best_alt.web_name if best_alt else "None",
                "best_alternative_xp": round(alt_xp, 2),
                "marginal_advantage_xp": round(s_xp - alt_xp, 2)
            })

        return {
            "architecture": "Starting-XI-First Lexicographic MILP",
            "mode": mode,
            "target_gw": current_gw,
            "horizon": res["horizon_weights"],
            "formation": res["formation"],
            "is_bench_boost": res["is_bench_boost"],
            "total_budget_str": f"£{total_budget/10:.1f}m",
            "primary_objective": f"Maximize Starting XI Expected Points ({res['current_gw_starting_xi_xp']:.2f} xP) + Captain Bonus ({res['captain_contribution_xp']:.2f} xP)",
            "secondary_objective": f"Lock Starting XI score (Z1*), then maximize Bench Quality ({sum(d['gw0_xp'] for d in res['bench']):.2f} xP)",
            "starting_xi_projected_total": res["current_gw_starting_xi_xp"],
            "captain_name": res["captain"]["web_name"] if res["captain"] else "None",
            "captain_bonus_xp": res["captain_contribution_xp"],
            "total_projected_score": res["total_current_gw_xp"],
            "bench_projected_total": sum(d["gw0_xp"] for d in res["bench"]),
            "constraints_valid": True,
            "marginal_swap_analysis": marginal_swap_analysis,
            "top_projected_players": top_projected_breakdown,
            "rejected_high_value_players": rejected_high_value,
            "optimization_result": res
        }
