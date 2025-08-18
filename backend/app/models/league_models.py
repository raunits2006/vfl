from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, Integer, ForeignKey
from pydantic import field_validator

if TYPE_CHECKING:
    from .user_model import User
    from .player_pool_model import Players

class LeagueStatus(str, Enum):
    DRAFTING = "DRAFTING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"

class DraftStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class TradeStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class League(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: Optional[str] = None
    max_teams: int = Field(default=8)
    status: LeagueStatus = Field(default=LeagueStatus.DRAFTING)
    # 6-digit PIN used to join a league
    join_pin: Optional[str] = Field(default=None, description="6-digit code to join league", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    members: List["LeagueMember"] = Relationship(back_populates="league")
    teams: List["Team"] = Relationship(back_populates="league")
    settings: "LeagueSettings" = Relationship(back_populates="league")
    draft_sessions: List["DraftSession"] = Relationship(back_populates="league")
    trades: List["Trade"] = Relationship(back_populates="league")

class LeagueMember(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: int = Field(foreign_key="league.id")
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False))
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_commissioner: bool = Field(default=False)
    
    # Relationships
    league: League = Relationship(back_populates="members")
    user: "User" = Relationship(back_populates="league_memberships")

class LeagueSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: int = Field(foreign_key="league.id", unique=True)
    
    # Roster settings
    max_players: int = Field(default=7)
    starting_players: int = Field(default=5)
    bench_players: int = Field(default=2)
    
    # Scoring settings
    points_per_kill: float = Field(default=1.0)
    points_per_assist: float = Field(default=0.25)
    use_best_2_of_3: bool = Field(default=True, description="Award points for best 2 maps out of 3")
    # Agent prediction multipliers
    agent_exact_match_multiplier: float = Field(default=1.0, description="Multiplier if agent exact picks match (full points)")
    agent_class_match_multiplier: float = Field(default=0.5, description="Multiplier if agent class matches any picked class")
    agent_miss_multiplier: float = Field(default=0.25, description="Multiplier if no picks/classes match")
    
    # Draft settings
    draft_type: str = Field(default="snake")  # snake, auction, etc.
    draft_order: Optional[str] = None  # JSON string of user IDs in draft order
    
    # Relationships
    league: League = Relationship(back_populates="settings")

    @field_validator('agent_exact_match_multiplier', 'agent_class_match_multiplier', 'agent_miss_multiplier')
    @classmethod
    def validate_multiplier(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Multiplier cannot be negative')
        return v

class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: int = Field(foreign_key="league.id")
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False))
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    league: League = Relationship(back_populates="teams")
    user: "User" = Relationship(back_populates="teams")
    players: List["TeamPlayer"] = Relationship(back_populates="team")

class TeamPlayer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id")
    player_name: str = Field(foreign_key="players.player_name")  # Reference to Players table
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_starting: bool = Field(default=False)  # True = starting, False = bench
    
    # Relationships
    team: Team = Relationship(back_populates="players")

class AgentPrediction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id")
    player_name: str = Field(foreign_key="players.player_name")
    # comma-separated list of three agent names, stored uppercase/literal
    picks_csv: str = Field(description="Comma-separated list of three chosen agents")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    team: "Team" = Relationship()
    player: "Players" = Relationship()

    @field_validator('picks_csv')
    @classmethod
    def validate_picks_csv(cls, v: str) -> str:
        picks = [p.strip() for p in v.split(',') if p.strip()]
        if len(picks) != 3:
            raise ValueError('picks_csv must contain exactly 3 agents')
        # Store as uppercase as per comment
        return ','.join(p.upper() for p in picks)

# Draft System Models
class DraftSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: int = Field(foreign_key="league.id")
    status: DraftStatus = Field(default=DraftStatus.PENDING)
    current_pick: int = Field(default=1)
    current_user_id: Optional[int] = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    # New fields for draft order and timer
    draft_order: Optional[str] = Field(default=None, description="JSON list of user IDs in draft order")
    current_pick_index: int = Field(default=0, description="Index in draft_order for current pick")
    pick_deadline: Optional[datetime] = Field(default=None, description="Deadline for current pick (UTC)")
    
    # Relationships
    league: League = Relationship(back_populates="draft_sessions")
    picks: List["DraftPick"] = Relationship(back_populates="draft_session")

class DraftPick(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    draft_session_id: int = Field(foreign_key="draftsession.id")
    team_id: int = Field(foreign_key="team.id")
    player_name: str = Field(foreign_key="players.player_name")
    pick_number: int
    picked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    draft_session: DraftSession = Relationship(back_populates="picks")
    team: Team = Relationship()

# Trade System Models
class Trade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: int = Field(foreign_key="league.id")
    team1_id: int = Field(foreign_key="team.id")
    team2_id: int = Field(foreign_key="team.id")
    status: TradeStatus = Field(default=TradeStatus.PENDING)
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responded_at: Optional[datetime] = None
    
    # Relationships
    league: League = Relationship(back_populates="trades")
    trade_items: List["TradeItem"] = Relationship(back_populates="trade")

class TradeItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    trade_id: int = Field(foreign_key="trade.id")
    team_id: int = Field(foreign_key="team.id")
    player_name: str = Field(foreign_key="players.player_name")
    
    # Relationships
    trade: Trade = Relationship(back_populates="trade_items")
    team: Team = Relationship()

# Free Agent System Models
class FreeAgentTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    league_id: int = Field(foreign_key="league.id")
    team_id: int = Field(foreign_key="team.id")
    player_name: str = Field(foreign_key="players.player_name")
    transaction_type: str = Field()  # "add", "drop"
    transaction_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    league: League = Relationship()
    team: Team = Relationship() 