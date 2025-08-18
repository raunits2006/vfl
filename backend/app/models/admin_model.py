from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class Admin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str = Field()
    is_active: bool = Field(default=True)
    is_super_admin: bool = Field(default=False, description="Super admin with all permissions")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = Field(default=None)
    
    # Permissions
    can_manage_players: bool = Field(default=True)
    can_manage_users: bool = Field(default=False)
    can_manage_leagues: bool = Field(default=False)
    can_manage_matches: bool = Field(default=False)
    can_view_analytics: bool = Field(default=True)
