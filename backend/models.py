from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from backend.database import Base

class ElementType(str, enum.Enum):
    GKP = "GKP"
    DEF = "DEF"
    MID = "MID"
    FWD = "FWD"

POSITION_MAP = {
    1: ElementType.GKP,
    2: ElementType.DEF,
    3: ElementType.MID,
    4: ElementType.FWD
}

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    short_name = Column(String(10), nullable=False)
    code = Column(Integer, nullable=True)
    strength = Column(Integer, default=3)
    strength_overall_home = Column(Integer, default=1000)
    strength_overall_away = Column(Integer, default=1000)
    strength_attack_home = Column(Integer, default=1000)
    strength_attack_away = Column(Integer, default=1000)
    strength_defence_home = Column(Integer, default=1000)
    strength_defence_away = Column(Integer, default=1000)
    
    players = relationship("Player", back_populates="team")
    home_fixtures = relationship("Fixture", foreign_keys="Fixture.team_h_id", back_populates="home_team")
    away_fixtures = relationship("Fixture", foreign_keys="Fixture.team_a_id", back_populates="away_team")

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)  # FPL element ID
    code = Column(Integer, nullable=True)
    web_name = Column(String(100), nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    second_name = Column(String(100), nullable=True)
    
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    element_type = Column(String(10), nullable=False)  # GKP, DEF, MID, FWD
    
    now_cost = Column(Integer, nullable=False)  # Price in tenths (e.g. 100 = £10.0m)
    status = Column(String(10), default="a")  # a: available, d: doubtful, i: injured, s: suspended, u: unavailable
    chance_of_playing_next_round = Column(Integer, nullable=True)
    news = Column(Text, nullable=True)
    news_added = Column(DateTime, nullable=True)
    
    # Stats
    total_points = Column(Integer, default=0)
    event_points = Column(Integer, default=0)
    minutes = Column(Integer, default=0)
    goals_scored = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    clean_sheets = Column(Integer, default=0)
    goals_conceded = Column(Integer, default=0)
    own_goals = Column(Integer, default=0)
    penalties_saved = Column(Integer, default=0)
    penalties_missed = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    bonus = Column(Integer, default=0)
    bps = Column(Integer, default=0)
    
    # Underlying stats (xG, xA, etc.)
    expected_goals = Column(Float, default=0.0)
    expected_assists = Column(Float, default=0.0)
    expected_goal_involvements = Column(Float, default=0.0)
    expected_goals_conceded = Column(Float, default=0.0)
    
    # 2026/27 DEFCON stats (Clearances, Blocks, Interceptions, Tackles for defenders)
    defensive_contributions = Column(Integer, default=0)  # CBIT total count
    
    selected_by_percent = Column(Float, default=0.0)
    form = Column(Float, default=0.0)
    ep_next = Column(Float, default=0.0)
    
    team = relationship("Team", back_populates="players")
    projections = relationship("PlayerProjection", back_populates="player", cascade="all, delete-orphan")

class Gameweek(Base):
    __tablename__ = "gameweeks"

    id = Column(Integer, primary_key=True, index=True)  # GW 1-38
    name = Column(String(50), nullable=False)
    deadline_time = Column(DateTime, nullable=True)
    average_entry_score = Column(Integer, default=0)
    highest_score = Column(Integer, default=0)
    is_previous = Column(Boolean, default=False)
    is_current = Column(Boolean, default=False)
    is_next = Column(Boolean, default=False)
    finished = Column(Boolean, default=False)
    data_checked = Column(Boolean, default=False)
    
    fixtures = relationship("Fixture", back_populates="gameweek")
    projections = relationship("PlayerProjection", back_populates="gameweek")

class Fixture(Base):
    __tablename__ = "fixtures"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("gameweeks.id"), nullable=True)
    
    team_h_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team_a_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    
    team_h_score = Column(Integer, nullable=True)
    team_a_score = Column(Integer, nullable=True)
    
    kickoff_time = Column(DateTime, nullable=True)
    finished = Column(Boolean, default=False)
    minutes = Column(Integer, default=0)
    
    team_h_difficulty = Column(Integer, default=3)
    team_a_difficulty = Column(Integer, default=3)
    
    gameweek = relationship("Gameweek", back_populates="fixtures")
    home_team = relationship("Team", foreign_keys=[team_h_id], back_populates="home_fixtures")
    away_team = relationship("Team", foreign_keys=[team_a_id], back_populates="away_fixtures")

class GameweekTeamSnapshot(Base):
    __tablename__ = "gameweek_team_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    fpl_entry_id = Column(Integer, nullable=True, index=True)
    gameweek_id = Column(Integer, ForeignKey("gameweeks.id"), nullable=False, index=True)

    picks_json = Column(Text, nullable=False)
    starting_xi_ids = Column(Text, nullable=False)
    bench_ids = Column(Text, nullable=False)

    captain_id = Column(Integer, nullable=True)
    vice_captain_id = Column(Integer, nullable=True)
    active_chip = Column(String(50), default="none")

    starting_xi_points = Column(Integer, default=0)
    captain_bonus = Column(Integer, default=0)
    bench_points = Column(Integer, default=0)
    transfers_count = Column(Integer, default=0)
    points_cost = Column(Integer, default=0)
    net_gw_score = Column(Integer, default=0)

    overall_points = Column(Integer, nullable=True)
    overall_rank = Column(Integer, nullable=True)
    gw_rank = Column(Integer, nullable=True)
    bank = Column(Integer, default=0)
    team_value = Column(Integer, default=1000)

    is_final = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PlayerProjection(Base):
    __tablename__ = "player_projections"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False, index=True)
    gameweek_id = Column(Integer, ForeignKey("gameweeks.id"), nullable=False, index=True)
    
    source = Column(String(50), nullable=False, default="internal")  # 'internal', 'fpl_review', 'ffs', 'fffix', 'ensemble'
    expected_minutes = Column(Float, default=0.0)
    expected_points = Column(Float, default=0.0)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    player = relationship("Player", back_populates="projections")
    gameweek = relationship("Gameweek", back_populates="projections")

    __table_args__ = (
        UniqueConstraint('player_id', 'gameweek_id', 'source', name='uix_player_gw_source'),
    )

class UserSquad(Base):
    __tablename__ = "user_squads"

    id = Column(Integer, primary_key=True, index=True)
    fpl_entry_id = Column(Integer, nullable=True)
    name = Column(String(100), default="My FPL Team")
    bank = Column(Integer, default=0)  # In tenths (e.g. 15 = £1.5m)
    free_transfers = Column(Integer, default=1)
    active_chip = Column(String(30), nullable=True)  # 'wildcard', 'freehit', 'benchboost', 'triplecaptain'
    
    picks = relationship("UserPick", back_populates="squad", cascade="all, delete-orphan")

class UserPick(Base):
    __tablename__ = "user_picks"

    id = Column(Integer, primary_key=True, index=True)
    squad_id = Column(Integer, ForeignKey("user_squads.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    position = Column(Integer, nullable=False)  # 1 to 15
    is_captain = Column(Boolean, default=False)
    is_vice_captain = Column(Boolean, default=False)
    multiplier = Column(Integer, default=1)  # 0 for bench, 1 for starter, 2 for captain, 3 for triple captain
    
    squad = relationship("UserSquad", back_populates="picks")
    player = relationship("Player")
