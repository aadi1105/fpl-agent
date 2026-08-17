import requests
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Team, Player, Gameweek, Fixture, POSITION_MAP, ElementType

logger = logging.getLogger("fpl_ingestion")
logging.basicConfig(level=logging.INFO)

class FPLDataIngestion:
    def __init__(self, base_url: str = settings.FPL_API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def fetch_bootstrap_static(self) -> Dict[str, Any]:
        """Fetch bootstrap static data containing teams, players, gameweeks."""
        url = f"{self.base_url}/bootstrap-static/"
        logger.info(f"Fetching FPL bootstrap static data from {url}")
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def fetch_fixtures(self) -> List[Dict[str, Any]]:
        """Fetch all fixtures data."""
        url = f"{self.base_url}/fixtures/"
        logger.info(f"Fetching FPL fixtures data from {url}")
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def sync_teams(self, db: Session, teams_data: List[Dict[str, Any]]) -> int:
        """Upsert teams into the database."""
        synced_count = 0
        for t_data in teams_data:
            team_id = t_data["id"]
            team = db.query(Team).filter(Team.id == team_id).first()
            if not team:
                team = Team(id=team_id)
                db.add(team)

            team.name = t_data.get("name", "")
            team.short_name = t_data.get("short_name", "")
            team.code = t_data.get("code")
            team.strength = t_data.get("strength", 3)
            team.strength_overall_home = t_data.get("strength_overall_home", 1000)
            team.strength_overall_away = t_data.get("strength_overall_away", 1000)
            team.strength_attack_home = t_data.get("strength_attack_home", 1000)
            team.strength_attack_away = t_data.get("strength_attack_away", 1000)
            team.strength_defence_home = t_data.get("strength_defence_home", 1000)
            team.strength_defence_away = t_data.get("strength_defence_away", 1000)
            synced_count += 1

        db.commit()
        logger.info(f"Synced {synced_count} teams successfully.")
        return synced_count

    def sync_gameweeks(self, db: Session, events_data: List[Dict[str, Any]]) -> int:
        """Upsert gameweeks into the database."""
        synced_count = 0
        for gw_data in events_data:
            gw_id = gw_data["id"]
            gw = db.query(Gameweek).filter(Gameweek.id == gw_id).first()
            if not gw:
                gw = Gameweek(id=gw_id)
                db.add(gw)

            gw.name = gw_data.get("name", f"Gameweek {gw_id}")
            deadline_raw = gw_data.get("deadline_time")
            if deadline_raw:
                try:
                    gw.deadline_time = datetime.fromisoformat(deadline_raw.replace("Z", "+00:00"))
                except ValueError:
                    gw.deadline_time = None

            gw.average_entry_score = gw_data.get("average_entry_score", 0) or 0
            gw.highest_score = gw_data.get("highest_score", 0) or 0
            gw.is_previous = gw_data.get("is_previous", False)
            gw.is_current = gw_data.get("is_current", False)
            gw.is_next = gw_data.get("is_next", False)
            gw.finished = gw_data.get("finished", False)
            gw.data_checked = gw_data.get("data_checked", False)
            synced_count += 1

        db.commit()
        logger.info(f"Synced {synced_count} gameweeks successfully.")
        return synced_count

    def sync_players(self, db: Session, elements_data: List[Dict[str, Any]]) -> int:
        """Upsert players (elements) into the database."""
        synced_count = 0
        for p_data in elements_data:
            player_id = p_data["id"]
            player = db.query(Player).filter(Player.id == player_id).first()
            if not player:
                player = Player(id=player_id)
                db.add(player)

            player.code = p_data.get("code")
            player.web_name = p_data.get("web_name", "")
            player.first_name = p_data.get("first_name", "")
            player.second_name = p_data.get("second_name", "")
            player.team_id = p_data.get("team")

            elem_type_int = p_data.get("element_type", 1)
            player.element_type = POSITION_MAP.get(elem_type_int, ElementType.MID).value

            player.now_cost = p_data.get("now_cost", 0)
            player.status = p_data.get("status", "a")
            player.chance_of_playing_next_round = p_data.get("chance_of_playing_next_round")
            player.news = p_data.get("news")
            
            news_added_raw = p_data.get("news_added")
            if news_added_raw:
                try:
                    player.news_added = datetime.fromisoformat(news_added_raw.replace("Z", "+00:00"))
                except ValueError:
                    player.news_added = None

            player.total_points = p_data.get("total_points", 0)
            player.event_points = p_data.get("event_points", 0)
            player.minutes = p_data.get("minutes", 0)
            player.goals_scored = p_data.get("goals_scored", 0)
            player.assists = p_data.get("assists", 0)
            player.clean_sheets = p_data.get("clean_sheets", 0)
            player.goals_conceded = p_data.get("goals_conceded", 0)
            player.own_goals = p_data.get("own_goals", 0)
            player.penalties_saved = p_data.get("penalties_saved", 0)
            player.penalties_missed = p_data.get("penalties_missed", 0)
            player.yellow_cards = p_data.get("yellow_cards", 0)
            player.red_cards = p_data.get("red_cards", 0)
            player.saves = p_data.get("saves", 0)
            player.bonus = p_data.get("bonus", 0)
            player.bps = p_data.get("bps", 0)

            # Underlying metrics
            player.expected_goals = float(p_data.get("expected_goals", 0.0) or 0.0)
            player.expected_assists = float(p_data.get("expected_assists", 0.0) or 0.0)
            player.expected_goal_involvements = float(p_data.get("expected_goal_involvements", 0.0) or 0.0)
            player.expected_goals_conceded = float(p_data.get("expected_goals_conceded", 0.0) or 0.0)

            # Defensive contributions (CBIT - 2026/27 rule update if present in API)
            cbit_val = (
                p_data.get("clearances_blocks_interceptions", 0) +
                p_data.get("tackles", 0) +
                p_data.get("defensive_contributions", 0)
            )
            player.defensive_contributions = cbit_val

            player.selected_by_percent = float(p_data.get("selected_by_percent", 0.0) or 0.0)
            player.form = float(p_data.get("form", 0.0) or 0.0)
            player.ep_next = float(p_data.get("ep_next", 0.0) or 0.0)
            
            synced_count += 1

        db.commit()
        logger.info(f"Synced {synced_count} players successfully.")
        return synced_count

    def sync_fixtures(self, db: Session, fixtures_data: List[Dict[str, Any]]) -> int:
        """Upsert fixtures into the database."""
        synced_count = 0
        for f_data in fixtures_data:
            fixture_id = f_data["id"]
            fixture = db.query(Fixture).filter(Fixture.id == fixture_id).first()
            if not fixture:
                fixture = Fixture(id=fixture_id)
                db.add(fixture)

            fixture.event_id = f_data.get("event")
            fixture.team_h_id = f_data.get("team_h")
            fixture.team_a_id = f_data.get("team_a")
            fixture.team_h_score = f_data.get("team_h_score")
            fixture.team_a_score = f_data.get("team_a_score")

            kickoff_raw = f_data.get("kickoff_time")
            if kickoff_raw:
                try:
                    fixture.kickoff_time = datetime.fromisoformat(kickoff_raw.replace("Z", "+00:00"))
                except ValueError:
                    fixture.kickoff_time = None

            fixture.finished = f_data.get("finished", False)
            fixture.minutes = f_data.get("minutes", 0)
            fixture.team_h_difficulty = f_data.get("team_h_difficulty", 3)
            fixture.team_a_difficulty = f_data.get("team_a_difficulty", 3)
            synced_count += 1

        db.commit()
        logger.info(f"Synced {synced_count} fixtures successfully.")
        return synced_count

    def sync_all(self, db: Session) -> Dict[str, int]:
        """Perform full sync from FPL API."""
        static_data = self.fetch_bootstrap_static()
        fixtures_data = self.fetch_fixtures()

        teams_count = self.sync_teams(db, static_data.get("teams", []))
        gw_count = self.sync_gameweeks(db, static_data.get("events", []))
        players_count = self.sync_players(db, static_data.get("elements", []))
        fixtures_count = self.sync_fixtures(db, fixtures_data)

        return {
            "teams": teams_count,
            "gameweeks": gw_count,
            "players": players_count,
            "fixtures": fixtures_count
        }
