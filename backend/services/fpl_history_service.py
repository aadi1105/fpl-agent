import time
import requests
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Player, Team, Gameweek, Fixture, UserSquad, UserPick, PlayerProjection
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
        current_gw_id = CurrentGameStateManager(self.db).get_current_gameweek()

        results = []
        for g in gws:
            if g.id < current_gw_id:
                status = "COMPLETED"
            elif g.id == current_gw_id:
                status = "LIVE" if not g.finished else "COMPLETED"
            else:
                status = "UPCOMING"

            results.append({
                "id": g.id,
                "name": g.name or f"Gameweek {g.id}",
                "is_current": (g.id == current_gw_id),
                "is_next": (g.id == current_gw_id + 1),
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
        cache_key = f"entry_picks_{entry_id}_gw{gw}"
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
        current_gw_id = CurrentGameStateManager(self.db).get_current_gameweek()
        is_current_gw = (gw == current_gw_id)
        is_completed_gw = (gw < current_gw_id)
        is_future_gw = (gw > current_gw_id)

        # Get DB UserSquad to find default entry ID or fallback picks
        db_squad = self.db.query(UserSquad).first()
        effective_entry_id = fpl_entry_id or (db_squad.fpl_entry_id if db_squad else None) or 1

        # FUTURE GAMEWEEK: Show upcoming/projected squad with projected xP (NO FAKE ACTUAL POINTS)
        if is_future_gw:
            return self._build_future_gameweek_snapshot(gw, db_squad)

        # COMPLETED OR LIVE GAMEWEEK:
        # 1. Attempt fetching official FPL entry picks
        fpl_picks_data = self.fetch_fpl_entry_picks(effective_entry_id, gw)
        
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
            if db_squad and db_squad.picks:
                for pick in db_squad.picks:
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
                chip_used = db_squad.active_chip

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
                mult = 3 if chip_used == "triplecaptain" else 2
            elif p["is_vice_captain"] and vc_took_over:
                mult = 3 if chip_used == "triplecaptain" else 2

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
        net_gw_score = entry_history.get("points", starting_xi_points - transfers_cost)

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
            "overall_points": entry_history.get("total_points", starting_xi_points),
            "overall_rank": entry_history.get("overall_rank"),
            "gw_rank": entry_history.get("rank"),
            "active_chip": chip_used or "none",
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
