from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class LiveScore(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="match.id", nullable=False)
    team1_score: int
    team2_score: int
    current_map: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MapRound(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="match.id", nullable=False)
    map_name: str
    team1_rounds: int 
    team2_rounds: int 
    team1_attack_rounds: Optional[int] = Field(default=None)
    team1_defense_rounds: Optional[int] = Field(default=None)
    team2_attack_rounds: Optional[int] = Field(default=None)
    team2_defense_rounds: Optional[int] = Field(default=None)


class PlayerStat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="match.id", nullable=False)
    map_name: Optional[str] = None 
    player_name: str
    agent: Optional[str] = Field(default=None)
    kills: int
    deaths: int
    assists: int
    score: Optional[float] = Field(default=None)


