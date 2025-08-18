from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone # Import datetime and timezone
from pydantic import field_validator # Import field_validator


class MatchBase(SQLModel):
    team1: Optional[str] = Field(default=None)
    team2: Optional[str] = Field(default=None)
    match_series: Optional[str] = Field(default=None)
    match_event: Optional[str] = Field(default=None)
    unix_timestamp: Optional[int] = Field(default=None)
    match_page: str = Field(unique=True, index=True) # Assuming match_page is a unique identifier
    vlr_match_id: Optional[str] = Field(default=None)

class Match(MatchBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)

class MatchCreate(MatchBase):
    @field_validator("unix_timestamp", mode="before")
    @classmethod
    def convert_datetime_str_to_int(cls, value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int): # If it's already an int (e.g., from internal use or other API formats)
            return value
        if not isinstance(value, str):
            # This case should ideally not happen if input is consistently a string or None from the API
            raise ValueError("Unix timestamp input must be a datetime string (e.g., 'YYYY-MM-DD HH:MM:SS'), an integer, or None")
        
        try:
            # Parse the datetime string. Example format from error: '2025-05-17 11:00:00'
            dt_object_naive = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            # Assume the incoming datetime string is in UTC.
            # If it's in local time, you might need different timezone handling.
            dt_object_utc = dt_object_naive.replace(tzinfo=timezone.utc)
            return int(dt_object_utc.timestamp())
        except ValueError:
            # Pydantic will catch this and wrap it in its own ValidationError
            raise ValueError(f"Invalid datetime format for unix_timestamp: '{value}'. Expected 'YYYY-MM-DD HH:MM:SS'.")


class MatchRead(MatchBase):
    id: int
