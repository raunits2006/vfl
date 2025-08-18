from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, description="Agent name (e.g., 'Jett', 'Sova')")
    agent_class: str = Field(description="Agent class: Duelist, Controller, Initiator, or Sentinel")
    is_active: bool = Field(default=True, description="Whether this agent is currently available")
    release_date: Optional[str] = Field(default=None, description="Agent release date")
    image_url: Optional[str] = Field(default=None, description="URL to agent image/icon")
    description: Optional[str] = Field(default=None, description="Brief description of the agent")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
