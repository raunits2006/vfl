from fastapi import Depends
from sqlmodel import Session

from app.database import get_session
from app.utils.draft_utils import validate_team_not_locked


def enforce_team_unlocked(session: Session = Depends(get_session)) -> None:
    """FastAPI dependency that raises if the roster is currently locked."""
    validate_team_not_locked(session)


