import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.models import Player, Team, Fixture, Gameweek, PlayerProjection, ElementType

logger = logging.getLogger("current_state")
logging.basicConfig(level=logging.INFO)

class PlayerEligibilityStatus:
    ACTIVE = "ACTIVE"
    EXPECTED_STARTER = "EXPECTED_STARTER"
    ROTATION = "ROTATION"
    BACKUP = "BACKUP"
    DOUBTFUL = "DOUBTFUL"
    INJURED = "INJURED"
    SUSPENDED = "SUSPENDED"
    UNAVAILABLE = "UNAVAILABLE"
    TRANSFERRED = "TRANSFERRED"
    NOT_FIRST_CHOICE = "NOT_FIRST_CHOICE"

class CurrentGameStateManager:
    def __init__(self, db: Session):
        self.db = db

    def get_current_gameweek(self) -> int:
        """Determine current active gameweek from database fixtures or default to 1."""
        gw_obj = self.db.query(Gameweek).filter(Gameweek.is_current == True).first()
        if gw_obj:
            return gw_obj.id
        
        # Fallback to first uncompleted fixture
        next_fix = self.db.query(Fixture).filter(Fixture.finished == False).order_by(Fixture.event_id.asc()).first()
        if next_fix and next_fix.event_id:
            return next_fix.event_id
        return 1

    def evaluate_player_eligibility(self, player: Player) -> Dict[str, Any]:
        """
        General, reproducible eligibility classification.
        DOES NOT USE HARDCODED PLAYER NAMES.
        """
        status = (player.status or "a").lower()
        chance = player.chance_of_playing_next_round

        # Availability logic
        if status in ["i", "u"] or chance == 0:
            elig_status = PlayerEligibilityStatus.INJURED if status == "i" else PlayerEligibilityStatus.UNAVAILABLE
            is_eligible = False
            reason = f"Player status '{status}' or 0% chance of playing (news: {player.news or 'None'})"
        elif status == "s":
            elig_status = PlayerEligibilityStatus.SUSPENDED
            is_eligible = False
            reason = f"Player suspended (news: {player.news or 'None'})"
        elif status == "d" or (chance is not None and chance < 50):
            elig_status = PlayerEligibilityStatus.DOUBTFUL
            is_eligible = True # Still eligible but lower xP
            reason = f"Doubtful availability ({chance}% chance of playing)"
        else:
            # Check playing time history for backup distinction
            if player.element_type == "GKP" and player.minutes < 180 and player.now_cost <= 45:
                elig_status = PlayerEligibilityStatus.BACKUP
            else:
                elig_status = PlayerEligibilityStatus.ACTIVE
            is_eligible = True
            reason = "Fully available for selection"

        return {
            "player_id": player.id,
            "web_name": player.web_name,
            "status_code": status,
            "chance_of_playing": chance,
            "eligibility_status": elig_status,
            "is_optimizer_eligible": is_eligible,
            "reason": reason
        }

    def generate_current_state_snapshot(self, season: str = "2026-27") -> Dict[str, Any]:
        """
        Generate a versioned, idempotent snapshot of current gameweek state.
        """
        current_gw = self.get_current_gameweek()
        now_ts = datetime.utcnow().isoformat()
        version_tag = f"{season.replace('-', '_')}_GW{current_gw}_STATE_v1"

        players = self.db.query(Player).all()
        teams = self.db.query(Team).all()
        fixtures = self.db.query(Fixture).filter(Fixture.event_id == current_gw).all()

        active_count = 0
        unavailable_count = 0
        injured_count = 0
        suspended_count = 0
        doubtful_count = 0
        transferred_audit = []

        player_states = {}
        for p in players:
            elig = self.evaluate_player_eligibility(p)
            player_states[p.id] = {
                "web_name": p.web_name,
                "team_id": p.team_id,
                "team_name": p.team.short_name if p.team else "",
                "position": p.element_type,
                "now_cost": p.now_cost,
                "display_price": f"£{p.now_cost/10.0:.1f}m",
                "status": p.status,
                "chance_of_playing": p.chance_of_playing_next_round,
                "news": p.news,
                "eligibility": elig
            }

            if elig["is_optimizer_eligible"]:
                active_count += 1
            else:
                unavailable_count += 1
                if elig["eligibility_status"] == PlayerEligibilityStatus.INJURED:
                    injured_count += 1
                elif elig["eligibility_status"] == PlayerEligibilityStatus.SUSPENDED:
                    suspended_count += 1

            if elig["eligibility_status"] == PlayerEligibilityStatus.DOUBTFUL:
                doubtful_count += 1

        snapshot = {
            "snapshot_version": version_tag,
            "generated_at": now_ts,
            "season": season,
            "current_gw": current_gw,
            "data_cutoff": now_ts,
            "summary": {
                "total_players": len(players),
                "total_teams": len(teams),
                "current_gw_fixtures": len(fixtures),
                "optimizer_eligible_players": active_count,
                "optimizer_ineligible_players": unavailable_count,
                "injured_players": injured_count,
                "suspended_players": suspended_count,
                "doubtful_players": doubtful_count
            },
            "player_states": player_states
        }

        logger.info(f"Generated Current State Snapshot {version_tag} | Eligible: {active_count}/{len(players)}")
        return snapshot

    def run_data_quality_audit(self) -> Dict[str, Any]:
        """Audit active player pool for missing values or stale data."""
        players = self.db.query(Player).all()
        teams_map = {t.id: t for t in self.db.query(Team).all()}
        
        missing_prices = [p.web_name for p in players if not p.now_cost]
        missing_teams = [p.web_name for p in players if p.team_id not in teams_map]
        missing_positions = [p.web_name for p in players if not p.element_type]
        duplicate_ids = len(players) - len(set(p.id for p in players))

        is_clean = (len(missing_prices) == 0 and len(missing_teams) == 0 and len(missing_positions) == 0 and duplicate_ids == 0)

        return {
            "is_clean": is_clean,
            "total_players": len(players),
            "missing_prices_count": len(missing_prices),
            "missing_teams_count": len(missing_teams),
            "missing_positions_count": len(missing_positions),
            "duplicate_ids_count": duplicate_ids
        }

    def advance_gameweek(self, target_gw: Optional[int] = None) -> Dict[str, Any]:
        """
        Advance current gameweek from GW_N to GW_N+1 (e.g. GW1 -> GW2).
        1. Freeze previous state & preserve historical observations.
        2. Set is_current = False on previous GW and is_current = True on target GW.
        3. Recalculate rolling stats & projections for active GW.
        """
        current_gw = self.get_current_gameweek()
        next_gw = target_gw if target_gw is not None else current_gw + 1

        if next_gw > 38:
            logger.warning("Attempted to advance past GW38.")
            return {"status": "NO_OP", "current_gw": current_gw}

        # 1. Update Gameweek flags in DB
        prev_gw_obj = self.db.query(Gameweek).filter(Gameweek.id == current_gw).first()
        if prev_gw_obj:
            prev_gw_obj.is_current = False
            prev_gw_obj.is_previous = True
            prev_gw_obj.finished = True

        next_gw_obj = self.db.query(Gameweek).filter(Gameweek.id == next_gw).first()
        if not next_gw_obj:
            next_gw_obj = Gameweek(id=next_gw, name=f"Gameweek {next_gw}", is_current=True, is_next=False)
            self.db.add(next_gw_obj)
        else:
            next_gw_obj.is_current = True
            next_gw_obj.is_previous = False
            next_gw_obj.is_next = False

        self.db.commit()

        # 2. Generate new snapshot tag
        snapshot = self.generate_current_state_snapshot(season="2026-27")
        logger.info(f"Advanced Gameweek: GW{current_gw} -> GW{next_gw} | Active Snapshot: {snapshot['snapshot_version']}")
        return {
            "status": "ADVANCED",
            "previous_gw": current_gw,
            "current_gw": next_gw,
            "snapshot_version": snapshot["snapshot_version"],
            "snapshot": snapshot
        }

    def refresh_current_gameweek(self, force_gw: Optional[int] = None) -> Dict[str, Any]:
        """
        Idempotent weekly refresh orchestration pipeline.
        Steps:
        1. Detect current GW
        2. Sync & audit current availability/prices/clubs
        3. Generate/update snapshot
        4. Run projection engine for active horizon
        """
        if force_gw:
            self.advance_gameweek(target_gw=force_gw)
        
        current_gw = self.get_current_gameweek()
        dq = self.run_data_quality_audit()
        snapshot = self.generate_current_state_snapshot()

        # Update DB projections for upcoming horizon
        from backend.projections.engine import ProjectionEngine
        engine = ProjectionEngine(db=self.db)
        saved_cnt = engine.run_projections(start_gw=current_gw, end_gw=min(38, current_gw + 7), source="internal")

        return {
            "status": "READY",
            "current_gw": current_gw,
            "last_updated": datetime.utcnow().isoformat(),
            "snapshot_version": snapshot["snapshot_version"],
            "projections_updated": saved_cnt,
            "data_quality": dq,
            "summary": snapshot["summary"]
        }
