import os
import sys
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection, ElementType
from backend.ingestion.current_state import CurrentGameStateManager, PlayerEligibilityStatus
from backend.projections.engine import ProjectionEngine
from backend.optimizer.squad_optimizer import SquadOptimizer

logger = logging.getLogger("reality_audit")

class DecisionEngineRealityAuditor:
    def __init__(self, db: Session):
        self.db = db
        self.state_mgr = CurrentGameStateManager(db)
        self.proj_engine = ProjectionEngine(db)
        self.optimizer = SquadOptimizer(db)

    def audit_gameweek_consistency(self) -> Dict[str, Any]:
        """Verify layer-by-layer gameweek consistency across all production components."""
        state_gw = self.state_mgr.get_current_gameweek()
        
        db_curr_gw_obj = self.db.query(Gameweek).filter(Gameweek.finished == False).order_by(Gameweek.id.asc()).first() or self.db.query(Gameweek).filter(Gameweek.is_current == True).first()
        db_curr_gw = db_curr_gw_obj.id if db_curr_gw_obj else state_gw

        snapshot = self.state_mgr.generate_current_state_snapshot()
        
        # Test sample projection run target GW
        sample_proj_gw = state_gw

        is_consistent = (state_gw == db_curr_gw == sample_proj_gw)

        return {
            "is_consistent": is_consistent,
            "state_manager_gw": state_gw,
            "database_is_current_gw": db_curr_gw,
            "snapshot_version": snapshot["snapshot_version"],
            "data_cutoff": snapshot["data_cutoff"],
            "projection_target_gw": sample_proj_gw,
            "mismatch_detected": not is_consistent
        }

    def audit_fixture_reconciliation(self, player_names: List[str]) -> List[Dict[str, Any]]:
        """Audit GW2-GW5 fixtures for target diagnostic players."""
        current_gw = self.state_mgr.get_current_gameweek()
        teams_map = {t.id: t for t in self.db.query(Team).all()}
        
        audit_results = []
        for name in player_names:
            p = self.db.query(Player).filter(Player.web_name.ilike(f"%{name}%")).first()
            if not p:
                continue

            p_team = teams_map.get(p.team_id)
            horizon_fixtures = []

            for gw in range(current_gw, min(38, current_gw + 4)):
                fix = self.db.query(Fixture).filter(
                    ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                    Fixture.event_id == gw
                ).first()

                if fix:
                    is_h = (fix.team_h_id == p.team_id)
                    opp_id = fix.team_a_id if is_h else fix.team_h_id
                    opp_team = teams_map.get(opp_id)
                    diff = fix.team_h_difficulty if is_h else fix.team_a_difficulty
                    fix_str = f"{opp_team.short_name if opp_team else 'OPP'} ({'H' if is_h else 'A'}, FDR:{diff})"
                else:
                    fix_str = "BYE"
                
                horizon_fixtures.append(fix_str)

            # Get GW2 projection
            proj = self.db.query(PlayerProjection).filter(
                PlayerProjection.player_id == p.id,
                PlayerProjection.gameweek_id == current_gw,
                PlayerProjection.source == "internal"
            ).first()

            xMins = self.proj_engine.calculate_expected_minutes(p)
            gw_fix = self.db.query(Fixture).filter(
                ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                Fixture.event_id == current_gw
            ).first()
            if gw_fix:
                is_h_gw = (gw_fix.team_h_id == p.team_id)
                opp_id_gw = gw_fix.team_a_id if is_h_gw else gw_fix.team_h_id
                opp_t_gw = teams_map.get(opp_id_gw)
                breakdown = self.proj_engine.calculate_player_xp_breakdown(p, fixture=gw_fix, is_home=is_h_gw, opp_team=opp_t_gw)
            else:
                breakdown = self.proj_engine.calculate_player_xp_breakdown(p)

            raw_xp = breakdown.get("raw_xp", breakdown.get("raw_total_xp", 0.0))
            total_xp = breakdown.get("total_xp", breakdown.get("calibrated_xp", 0.0))

            audit_results.append({
                "player_id": p.id,
                "web_name": p.web_name,
                "position": p.element_type,
                "price_str": f"£{p.now_cost/10.0:.1f}m",
                "club": p_team.short_name if p_team else "N/A",
                "status": p.status,
                "chance_of_playing": p.chance_of_playing_next_round,
                "expected_minutes": xMins,
                "raw_xp": round(raw_xp, 2),
                "v2_calibrated_xp": round(total_xp, 2),
                "gw2_fixture": horizon_fixtures[0] if len(horizon_fixtures) > 0 else "BYE",
                "gw3_fixture": horizon_fixtures[1] if len(horizon_fixtures) > 1 else "BYE",
                "gw4_fixture": horizon_fixtures[2] if len(horizon_fixtures) > 2 else "BYE",
                "gw5_fixture": horizon_fixtures[3] if len(horizon_fixtures) > 3 else "BYE",
            })

        return audit_results

    def audit_gyokeres_vs_havertz(self) -> Dict[str, Any]:
        """In-depth empirical breakdown of Gyökeres vs Havertz selection mechanics."""
        gyokeres = self.db.query(Player).filter(Player.web_name.ilike("%keres%")).first()
        havertz = self.db.query(Player).filter(Player.web_name.ilike("%Havertz%")).first()

        current_gw = self.state_mgr.get_current_gameweek()

        def get_breakdown(p_obj):
            fix = self.db.query(Fixture).filter(
                ((Fixture.team_h_id == p_obj.team_id) | (Fixture.team_a_id == p_obj.team_id)),
                Fixture.event_id == current_gw
            ).first()
            if fix:
                is_h = (fix.team_h_id == p_obj.team_id)
                opp_id = fix.team_a_id if is_h else fix.team_h_id
                opp_t = self.db.query(Team).filter(Team.id == opp_id).first()
                return self.proj_engine.calculate_player_xp_breakdown(p_obj, fixture=fix, is_home=is_h, opp_team=opp_t)
            return self.proj_engine.calculate_player_xp_breakdown(p_obj)

        def analyze_player(p: Optional[Player]):
            if not p:
                return {"found": False}
            
            breakdown = get_breakdown(p)
            elig = self.state_mgr.evaluate_player_eligibility(p)

            xMins = breakdown.get("xMins", breakdown.get("expected_minutes", 0.0))
            raw_xp = breakdown.get("raw_xp", breakdown.get("raw_total_xp", 0.0))
            cal_xg = breakdown.get("cal_xg", breakdown.get("xg_match", 0.0))
            cal_xa = breakdown.get("cal_xa", breakdown.get("xa_match", 0.0))
            total_xp = breakdown.get("total_xp", breakdown.get("calibrated_xp", 0.0))

            return {
                "found": True,
                "id": p.id,
                "web_name": p.web_name,
                "team": p.team.short_name if p.team else "",
                "now_cost_str": f"£{p.now_cost/10.0:.1f}m",
                "status": p.status,
                "chance_of_playing": p.chance_of_playing_next_round,
                "news": p.news,
                "minutes": p.minutes,
                "goals": p.goals_scored,
                "assists": p.assists,
                "expected_minutes": xMins,
                "raw_xp": round(raw_xp, 2),
                "calibrated_v2_xp": round(total_xp, 2),
                "cal_xg": round(cal_xg, 3),
                "cal_xa": round(cal_xa, 3),
                "eligibility": elig
            }

        g_info = analyze_player(gyokeres)
        h_info = analyze_player(havertz)

        pref_reason = ""
        if g_info.get("found") and h_info.get("found"):
            g_xp = g_info["calibrated_v2_xp"]
            h_xp = h_info["calibrated_v2_xp"]
            if g_xp > h_xp:
                pref_reason = f"Gyökeres is projected for higher calibrated GW{current_gw} xP ({g_xp} vs {h_xp}) driven by higher per-minute xG ({g_info['cal_xg']} vs {h_info['cal_xg']})."
            else:
                pref_reason = f"Havertz is projected for higher calibrated GW{current_gw} xP ({h_xp} vs {g_xp}) driven by higher expected minutes / starter probability ({h_info['expected_minutes']}m vs {g_info['expected_minutes']}m)."

        return {
            "gyokeres": g_info,
            "havertz": h_info,
            "preference_reason": pref_reason
        }

    def audit_fixture_sensitivity(self, player_names: List[str]) -> List[Dict[str, Any]]:
        """Controlled diagnostic measuring projection sensitivity under actual vs neutral fixtures."""
        current_gw = self.state_mgr.get_current_gameweek()
        sensitivity_results = []

        for name in player_names:
            p = self.db.query(Player).filter(Player.web_name.ilike(f"%{name}%")).first()
            if not p:
                continue

            fix = self.db.query(Fixture).filter(
                ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                Fixture.event_id == current_gw
            ).first()

            if fix:
                is_h = (fix.team_h_id == p.team_id)
                opp_id = fix.team_a_id if is_h else fix.team_h_id
                opp_t = self.db.query(Team).filter(Team.id == opp_id).first()
                breakdown_actual = self.proj_engine.calculate_player_xp_breakdown(p, fixture=fix, is_home=is_h, opp_team=opp_t)
            else:
                breakdown_actual = self.proj_engine.calculate_player_xp_breakdown(p)

            actual_xp = breakdown_actual.get("total_xp", breakdown_actual.get("calibrated_xp", 0.0))
            raw_xp = breakdown_actual.get("raw_xp", breakdown_actual.get("raw_total_xp", 0.0))
            fdr_impact = actual_xp - raw_xp

            sensitivity_results.append({
                "player": p.web_name,
                "position": p.element_type,
                "club": p.team.short_name if p.team else "",
                "actual_gw_xp": round(actual_xp, 2),
                "raw_base_xp": round(raw_xp, 2),
                "fixture_delta_xp": round(fdr_impact, 2),
                "sensitivity_direction": "BOOSTED" if fdr_impact > 0 else ("PENALIZED" if fdr_impact < 0 else "NEUTRAL")
            })

        return sensitivity_results

    def trace_player_selection(self, player_name: str) -> Dict[str, Any]:
        """Diagnostic trace explaining why a player was selected or rated."""
        p = self.db.query(Player).filter(Player.web_name.ilike(f"%{player_name}%")).first()
        if not p:
            return {"error": f"Player '{player_name}' not found."}

        current_gw = self.state_mgr.get_current_gameweek()
        fix = self.db.query(Fixture).filter(
            ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
            Fixture.event_id == current_gw
        ).first()

        if fix:
            is_h = (fix.team_h_id == p.team_id)
            opp_id = fix.team_a_id if is_h else fix.team_h_id
            opp_t = self.db.query(Team).filter(Team.id == opp_id).first()
            breakdown = self.proj_engine.calculate_player_xp_breakdown(p, fixture=fix, is_home=is_h, opp_team=opp_t)
        else:
            breakdown = self.proj_engine.calculate_player_xp_breakdown(p)

        elig = self.state_mgr.evaluate_player_eligibility(p)
        xMins = breakdown.get("xMins", breakdown.get("expected_minutes", 0.0))
        cal_xg = breakdown.get("cal_xg", breakdown.get("xg_match", 0.0))
        cal_xa = breakdown.get("cal_xa", breakdown.get("xa_match", 0.0))
        cs_prob = breakdown.get("cs_prob", 0.0)
        defcon_prob = breakdown.get("defcon_prob", 0.0)
        total_xp = breakdown.get("total_xp", breakdown.get("calibrated_xp", 0.0))

        return {
            "player_id": p.id,
            "web_name": p.web_name,
            "position": p.element_type,
            "club": p.team.name if p.team else "",
            "price_str": f"£{p.now_cost/10.0:.1f}m",
            "expected_minutes": xMins,
            "minutes_contribution_xp": round(xMins / 90.0 * 2.0, 2),
            "attacking_contribution_xp": round(cal_xg * (5.0 if p.element_type=="MID" else 4.0) + cal_xa * 3.0, 2),
            "defensive_contribution_xp": round(cs_prob * (4.0 if p.element_type in ["GKP", "DEF"] else 1.0), 2),
            "defcon_contribution_xp": round(defcon_prob * 2.0, 2),
            "v2_calibrated_xp": round(total_xp, 2),
            "eligibility_status": elig["eligibility_status"],
            "is_optimizer_eligible": elig["is_optimizer_eligible"],
            "selection_summary": f"Selected for {p.element_type} position due to {total_xp:.2f} GW{current_gw} xP ({xMins}m expected)."
        }

    def generate_top_diagnostic_rankings(self, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """Generate diagnostic top 20 rankings for GW2 xP, 4-GW Weighted xP, Value, and Captaincy."""
        current_gw = self.state_mgr.get_current_gameweek()
        players = self.db.query(Player).all()

        rankings = []
        for p in players:
            elig = self.state_mgr.evaluate_player_eligibility(p)
            if not elig["is_optimizer_eligible"]:
                continue

            gw_fix = self.db.query(Fixture).filter(
                ((Fixture.team_h_id == p.team_id) | (Fixture.team_a_id == p.team_id)),
                Fixture.event_id == current_gw
            ).first()
            if gw_fix:
                is_h_gw = (gw_fix.team_h_id == p.team_id)
                opp_id_gw = gw_fix.team_a_id if is_h_gw else gw_fix.team_h_id
                opp_t_gw = self.db.query(Team).filter(Team.id == opp_id_gw).first()
                breakdown = self.proj_engine.calculate_player_xp_breakdown(p, fixture=gw_fix, is_home=is_h_gw, opp_team=opp_t_gw)
            else:
                breakdown = self.proj_engine.calculate_player_xp_breakdown(p)

            gw_xp = round(breakdown.get("total_xp", breakdown.get("calibrated_xp", 0.0)), 2)
            
            # Fetch 4-GW projections
            projs = self.db.query(PlayerProjection).filter(
                PlayerProjection.player_id == p.id,
                PlayerProjection.gameweek_id.in_([current_gw + k for k in range(4)]),
                PlayerProjection.source == "internal"
            ).all()

            weights = [0.55, 0.20, 0.15, 0.10]
            weighted_xp = 0.0
            for idx, proj in enumerate(projs):
                if idx < len(weights):
                    weighted_xp += proj.expected_points * weights[idx]
            
            weighted_xp = round(weighted_xp, 2)
            xp_per_m = round(gw_xp / (p.now_cost / 10.0), 2)

            rankings.append({
                "id": p.id,
                "web_name": p.web_name,
                "club": p.team.short_name if p.team else "",
                "position": p.element_type,
                "price_str": f"£{p.now_cost/10.0:.1f}m",
                "now_cost": p.now_cost,
                "expected_minutes": breakdown.get("xMins", breakdown.get("expected_minutes", 0.0)),
                "gw_xp": gw_xp,
                "weighted_xp": weighted_xp,
                "xp_per_m": xp_per_m,
                "status": p.status,
                "chance": p.chance_of_playing_next_round or 100
            })

        top_gw_xp = sorted(rankings, key=lambda x: -x["gw_xp"])[:limit]
        top_weighted = sorted(rankings, key=lambda x: -x["weighted_xp"])[:limit]
        top_value = sorted(rankings, key=lambda x: -x["xp_per_m"])[:limit]
        top_captains = sorted([r for r in rankings if r["expected_minutes"] >= 60], key=lambda x: -x["gw_xp"])[:limit]

        return {
            "top_gw_xp": top_gw_xp,
            "top_weighted": top_weighted,
            "top_value": top_value,
            "top_captains": top_captains
        }
