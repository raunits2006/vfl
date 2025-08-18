from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .league_models import Team, LeagueMember

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    hashed_password: str = Field()
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    league_memberships: List["LeagueMember"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete"})
    teams: List["Team"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete"}) 