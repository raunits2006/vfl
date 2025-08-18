from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class Players(SQLModel, table=True):
    id: Optional[int] = Field(default=None)
    team: str 
    player_name: str = Field(primary_key=True)
    primary_role: Optional[str] = Field(default=None)
    image_url: Optional[str] = Field(default=None)
