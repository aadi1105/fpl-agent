import time
import json
import requests
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Player, Team, Gameweek, Fixture, UserSquad, UserPick, PlayerProjection, GameweekTeamSnapshot
from backend.projections.engine import ProjectionEngine
from backend.ingestion.current_state import CurrentGameStateManager

logger = logging.getLogger("fpl_history_service")

# In-memory cache: key -> (timestamp, data)
_HISTORY_CACHE: Dict[str, tuple[float, Any]] = {}
CACHE_TTL_LIVE = 60       # 60 seconds for live GW
CACHE_TTL_HISTORICAL = 3600 # 1 hour for completed GW
CACHE_TTL_FUTURE = 300     # 5 minutes for future GW

class FPLHistoryService:
    def __init__(self, db: Session):
        self.db = db
        self.base_url = settings.FPL_API_BASE_URL.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_all_gameweeks(self) -> List[Dict[str, Any]]:
        """Return list of all 38 Gameweeks with active current GW detection."""
        gws = self.db.query(Gameweek).order_by(Gameweek.id.asc()).all()
        active_gw_obj = self.db.query(Gameweek).filter(Gameweek.finished == False).order_by(Gameweek.id.asc()).first()
        active_gw_id = active_gw_obj.id if active_gw_obj else (CurrentGameStateManager(self.db).get_current_gameweek() + 1)

        results = []
        for g in gws:
            if g.finished:
                status = "COMPLETED"
            elif g.id == active_gw_id:
                status = "LIVE"
            else:
                status = "UPCOMING"

            results.append({
                "id": g.id,
                "name": g.name or f"Gameweek {g.id}",
                "is_current": (g.id == active_gw_id),
                "is_next": (g.id == active_gw_id + 1),
                "finished": g.finished,
                "deadline_time": g.deadline_time.isoformat() if g.deadline_time else None,
                "average_entry_score": g.average_entry_score or 0,
                "highest_score": g.highest_score or 0,
                "status": status
            })

        # Fallback if DB gameweeks table is sparse
        if not results:
            for gw_id in range(1, 39):
                status = "COMPLETED" if gw_id < current_gw_id else ("LIVE" if gw_id == current_gw_id else "UPCOMING")
                results.append({
                    "id": gw_id,
                    "name": f"Gameweek {gw_id}",
                    "is_current": (gw_id == current_gw_id),
                    "is_next": (gw_id == current_gw_id + 1),
                    "finished": (gw_id < current_gw_id),
                    "status": status
                })

        return results

    def fetch_fpl_live_elements(self, gw: int) -> Dict[int, Dict[str, Any]]:
        """Fetch live player statistics from FPL API for given GW, with caching and fallback."""
        cache_key = f"live_elements_{gw}"
        now = time.time()
        
        if cache_key in _HISTORY_CACHE:
            ts, cached_data = _HISTORY_CACHE[cache_key]
            current_gw = CurrentGameStateManager(self.db).get_current_gameweek()
            ttl = CACHE_TTL_LIVE if gw == current_gw else CACHE_TTL_HISTORICAL
            if now - ts < ttl:
                return cached_data

        live_map = {}
        try:
            url = f"{self.base_url}/event/{gw}/live/"
            logger.info(f"Fetching live FPL data from {url}")
            resp = self.session.get(url, timeout=6)
            if resp.ok:
                data = resp.json()
                for elem in data.get("elements", []):
                    elem_id = elem.get("id")
                    stats = elem.get("stats", {})
                    if elem_id:
                        live_map[elem_id] = {
                            "total_points": stats.get("total_points", 0),
                            "minutes": stats.get("minutes", 0),
                            "goals_scored": stats.get("goals_scored", 0),
                            "assists": stats.get("assists", 0),
                            "clean_sheets": stats.get("clean_sheets", 0),
                            "bonus": stats.get("bonus", 0),
                            "bps": stats.get("bps", 0),
                            "played": stats.get("played", False) or stats.get("minutes", 0) > 0
                        }
        except Exception as e:
            logger.warning(f"Could not fetch FPL live API for GW{gw}: {e}")

        # Fallback to DB player event_points / total_points if live API unavailable or empty
        if not live_map:
            players = self.db.query(Player).all()
            for p in players:
                live_map[p.id] = {
                    "total_points": p.event_points if p.event_points else (p.total_points or 0),
                    "minutes": p.minutes or 0,
                    "goals_scored": p.goals_scored or 0,
                    "assists": p.assists or 0,
                    "clean_sheets": p.clean_sheets or 0,
                    "bonus": p.bonus or 0,
                    "bps": p.bps or 0,
                    "played": (p.minutes > 0)
                }

        _HISTORY_CACHE[cache_key] = (now, live_map)
        return live_map

    def fetch_fpl_entry_picks(self, entry_id: int, gw: int) -> Optional[Dict[str, Any]]:
        """Fetch FPL manager entry picks for given GW from official FPL API."""
        cache_key = f"entry_picks_{entry_id}_gw_{gw}"
        now = time.time()
        
        if cache_key in _HISTORY_CACHE:
            ts, cached_data = _HISTORY_CACHE[cache_key]
            current_gw = CurrentGameStateManager(self.db).get_current_gameweek()
            ttl = CACHE_TTL_LIVE if gw == current_gw else CACHE_TTL_HISTORICAL
            if now - ts < ttl:
                return cached_data

        try:
            url = f"{self.base_url}/entry/{entry_id}/event/{gw}/picks/"
            logger.info(f"Fetching FPL entry picks from {url}")
            resp = self.session.get(url, timeout=6)
            if resp.ok:
                data = resp.json()
                _HISTORY_CACHE[cache_key] = (now, data)
                return data
        except Exception as e:
            logger.warning(f"Could not fetch FPL entry picks for entry {entry_id} GW{gw}: {e}")

        return None

    def get_gameweek_snapshot(self, gw: int, fpl_entry_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Build complete Gameweek Snapshot without mutating the user's saved current squad.
        """
        active_gw_obj = self.db.query(Gameweek).filter(Gameweek.finished == False).order_by(Gameweek.id.asc()).first()
        active_gw_id = active_gw_obj.id if active_gw_obj else 2

        target_gw_obj = self.db.query(Gameweek).filter(Gameweek.id == gw).first()

        is_completed_gw = target_gw_obj.finished if target_gw_obj else (gw < active_gw_id)
        is_current_gw = (gw == active_gw_id) and not is_completed_gw
        is_future_gw = (gw > active_gw_id) and not is_completed_gw

        # Get DB UserSquad to find default entry ID or fallback picks
        from backend.user.user_squad import UserSquadManager
        db_squad = UserSquadManager(self.db).get_or_create_user_squad()
        configured_entry_id = db_squad.fpl_entry_id if db_squad else None

        # Validate requested entry ID against configured manager entry ID
        if fpl_entry_id is not None and configured_entry_id is not None:
            if fpl_entry_id != configured_entry_id:
                return {
                    "error": True,
                    "error_code": "MANAGER_MISMATCH",
                    "message": f"FPL Manager Data Mismatch: Expected Entry ID {configured_entry_id}, got {fpl_entry_id}"
                }

    def _normalize_chip_name(self, chip: Optional[str]) -> str:
        if not chip or str(chip).lower().strip() in ["none", "null", ""]:
            return "none"
        c = str(chip).lower().strip()
        if c in ["bboost", "benchboost", "bench_boost"]:
            return "benchboost"
        if c in ["3xc", "triplecaptain", "triple_captain"]:
            return "triplecaptain"
        if c in ["wildcard"]:
            return "wildcard"
        if c in ["freehit", "free_hit"]:
            return "freehit"
        return c

    def _format_chip_display(self, chip: Optional[str]) -> str:
        norm = self._normalize_chip_name(chip)
        mapping = {
            "benchboost": "BENCH BOOST",
            "triplecaptain": "TRIPLE CAPTAIN",
            "wildcard": "WILDCARD",
            "freehit": "FREE HIT",
            "none": "NONE"
        }
        return mapping.get(norm, norm.upper())

    def get_used_chips_map(self, target_entry_id: Optional[int] = None) -> Dict[str, int]:
        """Return dict mapping chip_key -> gameweek_id where used (e.g. {'benchboost': 2})."""
        used_map = {}

        # 1. Official FPL API history if linked
        if target_entry_id:
            try:
                url = f"{self.base_url}/entry/{target_entry_id}/history/"
                resp = self.session.get(url, timeout=5)
                if resp.ok:
                    data = resp.json()
                    for c in data.get("chips", []):
                        cname = self._normalize_chip_name(c.get("name", ""))
                        cevent = c.get("event")
                        if cname != "none" and cevent:
                            used_map[cname] = cevent
            except Exception as e:
                logger.warning(f"Error fetching official chip history: {e}")

        # 2. Local DB frozen snapshots
        snaps = self.db.query(GameweekTeamSnapshot).filter(
            GameweekTeamSnapshot.active_chip.isnot(None),
            GameweekTeamSnapshot.active_chip != "none"
        ).all()
        for s in snaps:
            cname = self._normalize_chip_name(s.active_chip)
            if cname != "none":
                used_map[cname] = s.gameweek_id

        # 3. Current UserSquad active_chip
        from backend.user.user_squad import UserSquadManager
        db_squad = UserSquadManager(self.db).get_or_create_user_squad()
        if db_squad and db_squad.active_chip:
            cname = self._normalize_chip_name(db_squad.active_chip)
            if cname != "none" and cname not in used_map:
                from backend.ingestion.current_state import CurrentGameStateManager
                curr_gw = CurrentGameStateManager(self.db).get_current_gameweek()
                used_map[cname] = curr_gw

        return used_map

    def get_gameweek_snapshot(self, gw: int, fpl_entry_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Retrieve snapshot for specified Gameweek.
        Returns historical snapshot if completed, live statistics if current, or projected roster if future.
        """
        active_gw_id = CurrentGameStateManager(self.db).get_current_gameweek()
        is_completed_gw = (gw < active_gw_id)
        is_current_gw = (gw == active_gw_id)
        is_future_gw = (gw > active_gw_id)

        # Get DB UserSquad to find default entry ID or fallback picks
        from backend.user.user_squad import UserSquadManager
        db_squad = UserSquadManager(self.db).get_or_create_user_squad()
        configured_entry_id = db_squad.fpl_entry_id if db_squad else None

        # Validate requested entry ID against configured manager entry ID
        if fpl_entry_id is not None and configured_entry_id is not None:
            if fpl_entry_id != configured_entry_id:
                return {
                    "error": True,
                    "error_code": "MANAGER_MISMATCH",
                    "message": f"FPL Manager Data Mismatch: Expected Entry ID {configured_entry_id}, got {fpl_entry_id}"
                }

        target_entry_id = fpl_entry_id or configured_entry_id

        # FUTURE GAMEWEEK: Show upcoming/projected squad with projected xP (NO FAKE ACTUAL POINTS)
        if is_future_gw:
            return self._build_future_gameweek_snapshot(gw, db_squad)

        # IMMUTABLE COMPLETED GAMEWEEK SNAPSHOT: Check if frozen snapshot exists in DB
        if is_completed_gw:
            db_snap = self.db.query(GameweekTeamSnapshot).filter(
                GameweekTeamSnapshot.gameweek_id == gw,
                GameweekTeamSnapshot.fpl_entry_id == target_entry_id,
                GameweekTeamSnapshot.is_final == True
            ).first()
            if db_snap and db_snap.picks_json:
                try:
                    picks_list = json.loads(db_snap.picks_json)
                    starters = [p for p in picks_list if p.get("is_starter")]
                    bench = [p for p in picks_list if not p.get("is_starter")]

                    # Compute cumulative overall points up to this GW
                    cum_pts = 0
                    for prev_g in range(1, gw + 1):
                        prev_s = self.db.query(GameweekTeamSnapshot).filter(
                            GameweekTeamSnapshot.gameweek_id == prev_g,
                            GameweekTeamSnapshot.is_final == True
                        ).first()
                        if prev_s:
                            cum_pts += prev_s.net_gw_score
                        else:
                            cum_pts += db_snap.net_gw_score

                    return {
                        "gw": gw,
                        "status": "COMPLETED",
                        "is_live": False,
                        "is_completed": True,
                        "is_future": False,
                        "starting_xi_points": db_snap.starting_xi_points,
                        "captain_bonus": db_snap.captain_bonus,
                        "bench_points": db_snap.bench_points,
                        "transfers_count": db_snap.transfers_count,
                        "points_cost": db_snap.points_cost,
                        "net_gw_score": db_snap.net_gw_score,
                        "overall_points": cum_pts,
                        "overall_rank": db_snap.overall_rank,
                        "gw_rank": db_snap.gw_rank,
                        "active_chip": self._normalize_chip_name(db_snap.active_chip),
                        "active_chip_display": self._format_chip_display(db_snap.active_chip),
                        "vc_took_over": False,
                        "starting_11": starters,
                        "bench": bench,
                        "picks": picks_list
                    }
                except Exception as e:
                    logger.warning(f"Error parsing frozen snapshot for GW{gw}: {e}")

        # COMPLETED OR LIVE GAMEWEEK:
        # 1. Attempt fetching official FPL entry picks ONLY if explicit entry_id is configured
        fpl_picks_data = None
        if target_entry_id is not None:
            fpl_picks_data = self.fetch_fpl_entry_picks(target_entry_id, gw)
        
        # 2. Fetch live/actual player statistics
        live_stats_map = self.fetch_fpl_live_elements(gw)

        # 3. Fetch projection engine for expected points comparison
        engine = ProjectionEngine(self.db)
        players_map = {p.id: p for p in self.db.query(Player).all()}
        teams_map = {t.id: t for t in self.db.query(Team).all()}

        picks_list = []
        chip_used = None
        entry_history = {}

        if fpl_picks_data and "picks" in fpl_picks_data:
            chip_used = fpl_picks_data.get("active_chip")
            entry_history = fpl_picks_data.get("entry_history", {})
            auto_subs = fpl_picks_data.get("automatic_subs", [])

            for pk in fpl_picks_data["picks"]:
                elem_id = pk["element"]
                player_obj = players_map.get(elem_id)
                if not player_obj:
                    continue

                picks_list.append({
                    "id": player_obj.id,
                    "web_name": player_obj.web_name,
                    "position": player_obj.element_type,
                    "team_name": player_obj.team.short_name if player_obj.team else "",
                    "now_cost": player_obj.now_cost,
                    "now_cost_str": f"£{player_obj.now_cost / 10.0:.1f}m",
                    "position_order": pk.get("position", 1),
                    "is_starter": pk.get("position", 1) <= 11,
                    "is_captain": pk.get("is_captain", False),
                    "is_vice_captain": pk.get("is_vice_captain", False),
                    "multiplier": pk.get("multiplier", 1)
                })
        else:
            # Fallback to local DB UserSquad picks
            user_picks = db_squad.picks if (db_squad and db_squad.picks) else []
            if user_picks:
                for pick in user_picks:
                    p = pick.player
                    is_starter = (pick.position <= 11) or (pick.multiplier > 0)
                    picks_list.append({
                        "id": p.id,
                        "web_name": p.web_name,
                        "position": p.element_type,
                        "team_name": p.team.short_name if p.team else "",
                        "now_cost": p.now_cost,
                        "now_cost_str": f"£{p.now_cost / 10.0:.1f}m",
                        "position_order": pick.position,
                        "is_starter": is_starter,
                        "is_captain": pick.is_captain,
                        "is_vice_captain": pick.is_vice_captain,
                        "multiplier": pick.multiplier
                    })
                # Only use current db_squad active_chip for current Gameweek!
                chip_used = db_squad.active_chip if is_current_gw else "none"
            else:
                # Unconfigured default squad fallback
                gkps = self.db.query(Player).filter(Player.element_type == "GKP").limit(2).all()
                defs = self.db.query(Player).filter(Player.element_type == "DEF").limit(5).all()
                mids = self.db.query(Player).filter(Player.element_type == "MID").limit(5).all()
                fwds = self.db.query(Player).filter(Player.element_type == "FWD").limit(3).all()
                all_15 = gkps + defs + mids + fwds
                starters_set = set(gkps[:1] + defs[:3] + mids[:4] + fwds[:3])
                
                for idx, p in enumerate(all_15, start=1):
                    is_starter = p in starters_set
                    picks_list.append({
                        "id": p.id,
                        "web_name": p.web_name,
                        "position": p.element_type,
                        "team_name": p.team.short_name if p.team else "",
                        "now_cost": p.now_cost,
                        "now_cost_str": f"£{p.now_cost / 10.0:.1f}m",
                        "position_order": idx,
                        "is_starter": is_starter,
                        "is_captain": (idx == 1),
                        "is_vice_captain": (idx == 2),
                        "multiplier": 2 if idx == 1 else (1 if is_starter else 0)
                    })

        norm_chip = self._normalize_chip_name(chip_used)

        # Determine Captain / Vice-Captain Takeover
        cap_player = next((p for p in picks_list if p["is_captain"]), None)
        vc_player = next((p for p in picks_list if p["is_vice_captain"]), None)

        # Check if Captain played 0 mins
        cap_mins = live_stats_map.get(cap_player["id"], {}).get("minutes", 0) if cap_player else 0
        vc_took_over = (cap_player is not None and cap_mins == 0 and vc_player is not None)

        starters = [p for p in picks_list if p["is_starter"]]
        bench = [p for p in picks_list if not p["is_starter"]]

        starting_xi_points = 0
        captain_bonus = 0
        bench_points = 0

        # Calculate live / historical scores per player
        for p in picks_list:
            pid = p["id"]
            p_live = live_stats_map.get(pid, {})
            base_pts = p_live.get("total_points", 0)
            p["actual_pts"] = base_pts
            p["live_minutes"] = p_live.get("minutes", 0)
            p["played"] = p_live.get("played", False)

            # Calculate canonical projected xP for comparison
            proj = self.db.query(PlayerProjection).filter(
                PlayerProjection.player_id == pid,
                PlayerProjection.gameweek_id == gw,
                PlayerProjection.source == "internal"
            ).first()
            p["projected_xp"] = round(proj.expected_points, 2) if proj else 0.0

            # Determine multiplier
            mult = p.get("multiplier", 1 if p["is_starter"] else 0)
            if p["is_captain"]:
                mult = 3 if norm_chip == "triplecaptain" else 2
            elif p["is_vice_captain"] and vc_took_over:
                mult = 3 if norm_chip == "triplecaptain" else 2

            p["effective_multiplier"] = mult
            effective_pts = base_pts * mult

            if p["is_starter"]:
                starting_xi_points += effective_pts
                if p["is_captain"] and mult > 1:
                    captain_bonus += base_pts * (mult - 1)
                elif p["is_vice_captain"] and vc_took_over and mult > 1:
                    captain_bonus += base_pts * (mult - 1)
            else:
                bench_points += base_pts

        transfers_cost = entry_history.get("event_transfers_cost", 0)

        # Authoritative Final Gameweek Score Calculation:
        # STARTING XI RAW + CAPTAIN BONUS + (BENCH POINTS IF BENCH BOOST) - TRANSFER COST
        if norm_chip == "benchboost":
            calculated_gw_score = starting_xi_points + bench_points - transfers_cost
        else:
            calculated_gw_score = starting_xi_points - transfers_cost

        # Determine net_gw_score
        if norm_chip == "benchboost" and entry_history.get("points") is not None:
            net_gw_score = max(entry_history.get("points", 0), calculated_gw_score)
        else:
            net_gw_score = entry_history.get("points", calculated_gw_score)

        # Compute cumulative overall points up to current gw
        cum_overall_pts = 0
        for prev_g in range(1, gw + 1):
            if prev_g == gw:
                cum_overall_pts += net_gw_score
            else:
                prev_s = self.db.query(GameweekTeamSnapshot).filter(
                    GameweekTeamSnapshot.gameweek_id == prev_g,
                    GameweekTeamSnapshot.is_final == True
                ).first()
                if prev_s:
                    cum_overall_pts += prev_s.net_gw_score
                else:
                    cum_overall_pts += 54  # Fallback for GW1 baseline if unpopulated

        # Freeze Completed Gameweek Snapshot in DB if not already saved
        if is_completed_gw and len(picks_list) == 15:
            try:
                new_snap = GameweekTeamSnapshot(
                    fpl_entry_id=target_entry_id,
                    gameweek_id=gw,
                    picks_json=json.dumps(picks_list),
                    starting_xi_ids=",".join(str(p["id"]) for p in starters),
                    bench_ids=",".join(str(p["id"]) for p in bench),
                    captain_id=cap_player["id"] if cap_player else None,
                    vice_captain_id=vc_player["id"] if vc_player else None,
                    active_chip=norm_chip,
                    starting_xi_points=starting_xi_points,
                    captain_bonus=captain_bonus,
                    bench_points=bench_points,
                    transfers_count=entry_history.get("event_transfers", 0),
                    points_cost=transfers_cost,
                    net_gw_score=net_gw_score,
                    overall_points=cum_overall_pts,
                    overall_rank=entry_history.get("overall_rank"),
                    gw_rank=entry_history.get("rank"),
                    bank=entry_history.get("bank", 0),
                    team_value=entry_history.get("value", 1000),
                    is_final=True
                )
                self.db.add(new_snap)
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                logger.warning(f"Could not persist GameweekTeamSnapshot for GW{gw}: {e}")

        return {
            "gw": gw,
            "status": "LIVE" if is_current_gw else "COMPLETED",
            "is_live": is_current_gw,
            "is_completed": is_completed_gw,
            "is_future": False,
            "starting_xi_points": starting_xi_points,
            "captain_bonus": captain_bonus,
            "bench_points": bench_points,
            "transfers_count": entry_history.get("event_transfers", 0),
            "points_cost": transfers_cost,
            "net_gw_score": net_gw_score,
            "overall_points": cum_overall_pts,
            "overall_rank": entry_history.get("overall_rank"),
            "gw_rank": entry_history.get("rank"),
            "active_chip": norm_chip,
            "active_chip_display": self._format_chip_display(norm_chip),
            "vc_took_over": vc_took_over,
            "starting_11": starters,
            "bench": bench,
            "picks": picks_list
        }

    def _build_future_gameweek_snapshot(self, gw: int, db_squad: Optional[UserSquad]) -> Dict[str, Any]:
        """Build future Gameweek snapshot showing projected team with NO fabricated actual points."""
        picks_list = []
        user_picks = db_squad.picks if (db_squad and db_squad.picks) else []

        if user_picks:
            for pick in user_picks:
                p = pick.player
                is_starter = (pick.position <= 11) or (pick.multiplier > 0)
                
                # Fetch projection for future GW
                proj = self.db.query(PlayerProjection).filter(
                    PlayerProjection.player_id == p.id,
                    PlayerProjection.gameweek_id == gw,
                    PlayerProjection.source == "internal"
                ).first()
                proj_xp = round(proj.expected_points, 2) if proj else 0.0

                picks_list.append({
                    "id": p.id,
                    "web_name": p.web_name,
                    "position": p.element_type,
                    "team_name": p.team.short_name if p.team else "",
                    "now_cost": p.now_cost,
                    "now_cost_str": f"£{p.now_cost / 10.0:.1f}m",
                    "position_order": pick.position,
                    "is_starter": is_starter,
                    "is_captain": pick.is_captain,
                    "is_vice_captain": pick.is_vice_captain,
                    "multiplier": pick.multiplier,
                    "actual_pts": None,  # NO FAKE POINTS FOR FUTURE GWs!
                    "projected_xp": proj_xp
                })
        else:
            # Unconfigured fallback picks
            gkps = self.db.query(Player).filter(Player.element_type == "GKP").limit(2).all()
            defs = self.db.query(Player).filter(Player.element_type == "DEF").limit(5).all()
            mids = self.db.query(Player).filter(Player.element_type == "MID").limit(5).all()
            fwds = self.db.query(Player).filter(Player.element_type == "FWD").limit(3).all()
            all_15 = gkps + defs + mids + fwds
            starters_set = set(gkps[:1] + defs[:3] + mids[:4] + fwds[:3])
            
            for idx, p in enumerate(all_15, start=1):
                is_starter = p in starters_set
                proj = self.db.query(PlayerProjection).filter(
                    PlayerProjection.player_id == p.id,
                    PlayerProjection.gameweek_id == gw,
                    PlayerProjection.source == "internal"
                ).first()
                proj_xp = round(proj.expected_points, 2) if proj else 0.0

                picks_list.append({
                    "id": p.id,
                    "web_name": p.web_name,
                    "position": p.element_type,
                    "team_name": p.team.short_name if p.team else "",
                    "now_cost": p.now_cost,
                    "now_cost_str": f"£{p.now_cost / 10.0:.1f}m",
                    "position_order": idx,
                    "is_starter": is_starter,
                    "is_captain": (idx == 1),
                    "is_vice_captain": (idx == 2),
                    "multiplier": 2 if idx == 1 else (1 if is_starter else 0),
                    "actual_pts": None,
                    "projected_xp": proj_xp
                })

        starters = [p for p in picks_list if p["is_starter"]]
        bench = [p for p in picks_list if not p["is_starter"]]

        starting_xi_xp = sum(p["projected_xp"] * (p["multiplier"] if p["multiplier"] > 0 else 1) for p in starters)

        return {
            "gw": gw,
            "status": "UPCOMING",
            "is_live": False,
            "is_completed": False,
            "is_future": True,
            "starting_xi_points": None,
            "starting_xi_xp": round(starting_xi_xp, 2),
            "captain_bonus": 0,
            "bench_points": None,
            "transfers_count": 0,
            "points_cost": 0,
            "net_gw_score": None,
            "overall_points": None,
            "overall_rank": None,
            "gw_rank": None,
            "active_chip": db_squad.active_chip if db_squad else "none",
            "starting_11": starters,
            "bench": bench,
            "picks": picks_list
        }

    def get_season_history(self, fpl_entry_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Return comprehensive Season History table, compact season summary metrics, and chip status list.
        """
        db_squad = self.db.query(UserSquad).first()
        target_entry_id = fpl_entry_id or (db_squad.fpl_entry_id if db_squad else None)

        used_chips_map = self.get_used_chips_map(target_entry_id)

        all_gws = self.get_all_gameweeks()
        history_rows = []
        cum_points = 0
        best_gw = 0
        worst_gw = 999
        total_transfers = 0
        completed_or_live_count = 0
        latest_rank = None

        for gw_info in all_gws:
            gw_id = gw_info["id"]
            status = gw_info["status"]

            if status in ["COMPLETED", "LIVE"]:
                snap = self.get_gameweek_snapshot(gw_id, fpl_entry_id=target_entry_id)
                cap_name = next((p["web_name"] for p in snap.get("picks", []) if p.get("is_captain")), "—")
                net_pts = snap.get("net_gw_score", 0) or 0
                bench_pts = snap.get("bench_points", 0) or 0
                xfers = snap.get("transfers_count", 0) or 0
                cost = snap.get("points_cost", 0) or 0
                chip = snap.get("active_chip", "none")

                cum_points += net_pts
                completed_or_live_count += 1
                best_gw = max(best_gw, net_pts)
                worst_gw = min(worst_gw, net_pts)
                total_transfers += xfers

                raw_rank = snap.get("overall_rank")
                if raw_rank:
                    latest_rank = raw_rank
                rank_display = raw_rank if raw_rank else ("NOT_LINKED" if target_entry_id is None else "N/A")

                history_rows.append({
                    "gw": gw_id,
                    "status": status,
                    "net_gw_score": net_pts,
                    "captain_name": cap_name,
                    "bench_points": bench_pts,
                    "transfers_count": xfers,
                    "points_cost": cost,
                    "active_chip": self._format_chip_display(chip),
                    "overall_points": cum_points,
                    "overall_rank": rank_display,
                    "team_value_str": f"£{((snap.get('team_value') or 1000) / 10.0):.1f}m" if snap.get("team_value") else "£100.0m"
                })
            else:
                rank_display = "NOT_LINKED" if target_entry_id is None else "N/A"
                history_rows.append({
                    "gw": gw_id,
                    "status": "UPCOMING",
                    "net_gw_score": None,
                    "captain_name": "—",
                    "bench_points": None,
                    "transfers_count": 0,
                    "points_cost": 0,
                    "active_chip": "NONE",
                    "overall_points": cum_points,  # Preserves latest cumulative total!
                    "overall_rank": rank_display,
                    "team_value_str": "—"
                })

        gw_avg = round(cum_points / completed_or_live_count, 1) if completed_or_live_count > 0 else 0.0
        if worst_gw == 999:
            worst_gw = 0

        # Build Chip Status List for 4 FPL Chips
        chips_status = [
            {
                "key": "wildcard",
                "label": "Wildcard",
                "status": f"USED — GW{used_chips_map['wildcard']}" if "wildcard" in used_chips_map else "AVAILABLE",
                "is_used": "wildcard" in used_chips_map,
                "used_gw": used_chips_map.get("wildcard")
            },
            {
                "key": "freehit",
                "label": "Free Hit",
                "status": f"USED — GW{used_chips_map['freehit']}" if "freehit" in used_chips_map else "AVAILABLE",
                "is_used": "freehit" in used_chips_map,
                "used_gw": used_chips_map.get("freehit")
            },
            {
                "key": "benchboost",
                "label": "Bench Boost",
                "status": f"USED — GW{used_chips_map['benchboost']}" if "benchboost" in used_chips_map else "AVAILABLE",
                "is_used": "benchboost" in used_chips_map,
                "used_gw": used_chips_map.get("benchboost")
            },
            {
                "key": "triplecaptain",
                "label": "Triple Captain",
                "status": f"USED — GW{used_chips_map['triplecaptain']}" if "triplecaptain" in used_chips_map else "AVAILABLE",
                "is_used": "triplecaptain" in used_chips_map,
                "used_gw": used_chips_map.get("triplecaptain")
            },
        ]

        return {
            "history_rows": history_rows,
            "summary_metrics": {
                "total_points": cum_points,
                "gw_avg": gw_avg,
                "best_gw": best_gw,
                "worst_gw": worst_gw,
                "current_rank": latest_rank if latest_rank else ("NOT_LINKED" if target_entry_id is None else "N/A"),
                "total_transfers": total_transfers,
                "chips_used_count": len(used_chips_map)
            },
            "chips_status": chips_status,
            "used_chips_map": used_chips_map
        }
