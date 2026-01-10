from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import json
import random
from app.models.user_model import User

from app.database import get_session
from app.models.league_models import (
    DraftSession, DraftPick, DraftStatus, Team, League, TeamPlayer, LeagueMember, LeagueStatus
)
from app.models.player_pool_model import Players
from app.utils.draft_utils import (
    get_next_draft_state, validate_current_picker, get_draft_completion_info,
)
from app.utils.auth import get_current_active_user
# WebSocket imports moved to avoid circular import

# Draft configuration constants
DEFAULT_PICK_DEADLINE_MINUTES = 1

router = APIRouter(prefix="/drafts", tags=["drafts"])

def normalize_datetime_to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Return a UTC-aware datetime for comparison, handling naive values safely."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def auto_initialize_draft_order(session: Session, draft: DraftSession) -> bool:
    """Auto-initialize draft order from league members. Returns True if performed."""
    members = session.exec(select(LeagueMember).where(LeagueMember.league_id == draft.league_id)).all()
    if not members:
        return False
    user_ids = [m.user_id for m in members]
    random.shuffle(user_ids)
    draft.draft_order = json.dumps(user_ids)
    draft.current_pick_index = 0
    draft.current_user_id = user_ids[0]
    draft.status = DraftStatus.IN_PROGRESS
    draft.started_at = datetime.now(timezone.utc)
    draft.pick_deadline = draft.started_at + timedelta(minutes=DEFAULT_PICK_DEADLINE_MINUTES)
    session.add(draft)
    session.commit()
    return True

class StartDraftRequest(BaseModel):
    league_id: int

class DraftStatusResponse(BaseModel):
    draft_id: int
    league_id: int
    status: DraftStatus
    current_pick: int
    current_user_id: Optional[int]
    started_at: Optional[datetime]
    pick_deadline: Optional[datetime]
    completed_at: Optional[datetime]

class MakePickRequest(BaseModel):
    team_id: int
    player_name: str

class DraftPickResponse(BaseModel):
    id: int
    draft_session_id: int
    team_id: int
    player_name: str
    pick_number: int
    picked_at: datetime

class SetDraftOrderRequest(BaseModel):
    user_ids: List[int]
    randomize: bool = False

class DraftOrderResponse(BaseModel):
    draft_id: int
    draft_order: List[int]

@router.post("/start", response_model=DraftStatusResponse)
def start_draft(
    req: StartDraftRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Start a draft session for a league."""
    # Check if league exists
    league = session.exec(select(League).where(League.id == req.league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    # Check if draft already exists
    existing = session.exec(select(DraftSession).where(DraftSession.league_id == req.league_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Draft already started for this league")
    # Only a commissioner can start the draft
    membership = session.exec(
        select(LeagueMember).where(
            LeagueMember.league_id == req.league_id,
            LeagueMember.user_id == current_user.id
        )
    ).first()
    if not membership or not membership.is_commissioner:
        raise HTTPException(status_code=403, detail="Only the league commissioner can start the draft")
    # Create draft session
    draft = DraftSession(
        league_id=req.league_id,
        status=DraftStatus.PENDING,
        current_pick=1
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)

    # Do NOT auto-initialize order here. Keep draft PENDING until order is explicitly set.
    # Normalize datetimes to UTC-aware for consistent JSON (avoid client TZ drift)
    started = normalize_datetime_to_utc(draft.started_at)
    deadline = normalize_datetime_to_utc(draft.pick_deadline)
    return DraftStatusResponse(
        draft_id=draft.id,
        league_id=draft.league_id,
        status=draft.status,
        current_pick=draft.current_pick,
        current_user_id=draft.current_user_id,
        started_at=started,
        pick_deadline=deadline,
        completed_at=draft.completed_at
    )

@router.get("/by-league/{league_id}", response_model=DraftStatusResponse)
def get_draft_by_league(
    league_id: int,
    session: Session = Depends(get_session)
):
    """Get existing draft session for a league"""
    draft = session.exec(select(DraftSession).where(DraftSession.league_id == league_id)).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found for league")
    started = normalize_datetime_to_utc(draft.started_at)
    deadline = normalize_datetime_to_utc(draft.pick_deadline)
    return DraftStatusResponse(
        draft_id=draft.id,
        league_id=draft.league_id,
        status=draft.status,
        current_pick=draft.current_pick,
        current_user_id=draft.current_user_id,
        started_at=started,
        pick_deadline=deadline,
        completed_at=draft.completed_at
    )

@router.get("/{draft_id}/status", response_model=DraftStatusResponse)
def get_draft_status(
    draft_id: int,
    session: Session = Depends(get_session)
):
    draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    # Do not auto-initialize draft order here; wait for explicit set via POST /{draft_id}/order
    # Ensure active drafts always have a sane pick_deadline (~5 minutes). Fix bad data if far off.
    if draft.status == DraftStatus.IN_PROGRESS:
        now_utc = datetime.now(timezone.utc)
        deadline_utc = normalize_datetime_to_utc(draft.pick_deadline) if draft.pick_deadline else None
        if (
            deadline_utc is None or
            deadline_utc > now_utc + timedelta(minutes=30) or
            deadline_utc < now_utc - timedelta(hours=12)
        ):
            draft.pick_deadline = now_utc + timedelta(minutes=DEFAULT_PICK_DEADLINE_MINUTES)
            session.add(draft)
            session.commit()
    started = normalize_datetime_to_utc(draft.started_at)
    deadline = normalize_datetime_to_utc(draft.pick_deadline)
    return DraftStatusResponse(
        draft_id=draft.id,
        league_id=draft.league_id,
        status=draft.status,
        current_pick=draft.current_pick,
        current_user_id=draft.current_user_id,
        started_at=started,
        pick_deadline=deadline,
        completed_at=draft.completed_at
    )

@router.post("/{draft_id}/order", response_model=DraftOrderResponse)
def set_draft_order(
    draft_id: int,
    req: SetDraftOrderRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.PENDING:
        raise HTTPException(status_code=400, detail="Draft already started")
    
    # Validate that all user IDs exist
    if not req.user_ids:
        raise HTTPException(status_code=400, detail="Draft order cannot be empty")
    
    # Check if all user IDs exist in the database
    existing_users = session.exec(select(User).where(User.id.in_(req.user_ids))).all()
    existing_user_ids = {user.id for user in existing_users}
    invalid_user_ids = set(req.user_ids) - existing_user_ids
    
    if invalid_user_ids:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid user IDs: {list(invalid_user_ids)}. These users do not exist."
        )
    
    # Only allow league commissioner to set order
    membership = session.exec(
        select(LeagueMember).where(
            LeagueMember.league_id == draft.league_id,
            LeagueMember.user_id == current_user.id
        )
    ).first()
    if not membership or not membership.is_commissioner:
        raise HTTPException(status_code=403, detail="Only the league commissioner can set draft order")
    user_ids = req.user_ids[:]
    if req.randomize:
        random.shuffle(user_ids)
    draft.draft_order = json.dumps(user_ids)
    draft.current_pick_index = 0
    draft.current_user_id = user_ids[0] if user_ids else None
    session.add(draft)
    session.commit()
    draft.status = DraftStatus.IN_PROGRESS
    draft.started_at = datetime.now(timezone.utc)
    draft.pick_deadline = draft.started_at + timedelta(minutes=DEFAULT_PICK_DEADLINE_MINUTES)
    session.add(draft)
    session.commit()
    return DraftOrderResponse(draft_id=draft.id, draft_order=user_ids)

@router.get("/{draft_id}/order", response_model=DraftOrderResponse)
def get_draft_order(
    draft_id: int,
    session: Session = Depends(get_session)
):
    draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
    if not draft or not draft.draft_order:
        raise HTTPException(status_code=404, detail="Draft order not set")
    order = json.loads(draft.draft_order)
    return DraftOrderResponse(draft_id=draft.id, draft_order=order)

# Update make_pick to enforce order, timer, and autopick
@router.post("/{draft_id}/pick", response_model=DraftPickResponse)
def make_pick(
    draft_id: int,
    req: MakePickRequest,
    session: Session = Depends(get_session)
):
    draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != DraftStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Draft is not in progress")
    # Check if draft is complete
    total_picks_needed, is_complete = get_draft_completion_info(session, draft_id)
    if is_complete:
        raise HTTPException(status_code=400, detail="Draft is complete")

    # Validate current picker using snake draft logic
    if not validate_current_picker(session, draft_id, req.team_id):
        # Get the team to find the user_id
        team = session.exec(select(Team).where(Team.id == req.team_id)).first()
        if not team:
            raise HTTPException(status_code=400, detail="Team not found")

        if not validate_current_picker(session, draft_id, team.user_id):
            raise HTTPException(status_code=403, detail="Not your turn to pick")
    # Get team (already validated above)
    team = session.exec(select(Team).where(Team.id == req.team_id)).first()
    if not team or team.league_id != draft.league_id:
        raise HTTPException(status_code=400, detail="Team not in this league")
    # Timer logic
    now = datetime.now(timezone.utc)
    # Ensure pick_deadline is timezone-aware
    pick_deadline = draft.pick_deadline
    if pick_deadline and pick_deadline.tzinfo is None:
        pick_deadline = pick_deadline.replace(tzinfo=timezone.utc)
    
    # Check if deadline has passed
    if pick_deadline and now > pick_deadline:
        # Autopick for user - use the same logic as the background task
        from app.workers.draft_autopick import _perform_autopick
        success = _perform_autopick(draft_id, session)
        if not success:
            raise HTTPException(status_code=400, detail="Autopick failed")
        # Return the autopick result
        session.refresh(draft)
        latest_pick = session.exec(
            select(DraftPick).where(DraftPick.draft_session_id == draft_id).order_by(DraftPick.pick_number.desc())
        ).first()
        if latest_pick:
            return DraftPickResponse(
                id=latest_pick.id,
                draft_session_id=latest_pick.draft_session_id,
                team_id=latest_pick.team_id,
                player_name=latest_pick.player_name,
                pick_number=latest_pick.pick_number,
                picked_at=latest_pick.picked_at
            )
        else:
            raise HTTPException(status_code=400, detail="Autopick completed but no pick found")
    
    # Regular pick validation
    # Check if player exists in eligible player pool
    eligible_player = session.exec(select(Players).where(Players.player_name == req.player_name)).first()
    if not eligible_player:
        raise HTTPException(status_code=404, detail="Player is not an eligible fantasy player")
    # Check if player already picked in this draft
    existing_pick = session.exec(
        select(DraftPick).where(
            DraftPick.draft_session_id == draft_id,
            DraftPick.player_name == req.player_name
        )
    ).first()
    if existing_pick:
        raise HTTPException(status_code=400, detail="Player already drafted")
    
    # Note: Duelist player role restriction removed - only agent prediction duelist limit applies now
    
    # Add pick
    pick_number = draft.current_pick
    pick = DraftPick(
        draft_session_id=draft_id,
        team_id=req.team_id,
        player_name=req.player_name,
        pick_number=pick_number,
        picked_at=now
    )
    session.add(pick)
    # Add player to team roster
    team_player = TeamPlayer(
        team_id=req.team_id,
        player_name=req.player_name,
        is_starting=False
    )
    session.add(team_player)
    # Advance draft using snake draft logic
    current_pick_number = draft.current_pick
    next_user_id, is_draft_complete = get_next_draft_state(session, draft_id, current_pick_number)

    draft.current_pick += 1

    if is_draft_complete:
        draft.status = DraftStatus.COMPLETED
        draft.completed_at = now
        draft.current_user_id = None
        draft.pick_deadline = None
        # Also update the league status to ACTIVE now that drafting is complete
        league = session.exec(select(League).where(League.id == draft.league_id)).first()
        if league:
            league.status = LeagueStatus.ACTIVE
            # Keep timestamps consistent
            if hasattr(league, "updated_at"):
                league.updated_at = now
            session.add(league)
    else:
        draft.current_user_id = next_user_id
        draft.pick_deadline = datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_PICK_DEADLINE_MINUTES)
    session.add(draft)
    session.commit()
    session.refresh(pick)
    
    # Broadcast draft pick to WebSocket connections
    pick_data = {
        "pick_id": pick.id,
        "team_id": pick.team_id,
        "player_name": pick.player_name,
        "pick_number": pick.pick_number,
        "picked_at": pick.picked_at.isoformat(),
        "current_pick": draft.current_pick,
        "current_user_id": draft.current_user_id,
        "is_complete": is_draft_complete
    }
    
    # Broadcast to WebSocket connections
    try:
        from app.utils.websocket_manager import manager
        import asyncio, logging
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(manager.broadcast_to_draft({
                "type": "draft_pick",
                "draft_id": draft_id,
                **pick_data
            }, draft_id))
        except RuntimeError:
            logging.warning(f"Unable to broadcast draft pick for draft {draft_id} - not in async context")
    except ImportError as e:
        import logging
        logging.error(f"Failed to import websocket_manager: {e}")
    except Exception as e:
        import logging
        logging.error(f"Failed to broadcast draft pick: {e}")
    
    return DraftPickResponse(
        id=pick.id,
        draft_session_id=pick.draft_session_id,
        team_id=pick.team_id,
        player_name=pick.player_name,
        pick_number=pick.pick_number,
        picked_at=pick.picked_at
    )

@router.get("/{draft_id}/results", response_model=List[DraftPickResponse])
def get_draft_results(
    draft_id: int,
    session: Session = Depends(get_session)
):
    picks = session.exec(
        select(DraftPick).where(DraftPick.draft_session_id == draft_id).order_by(DraftPick.pick_number)
    ).all()
    return [
        DraftPickResponse(
            id=pick.id,
            draft_session_id=pick.draft_session_id,
            team_id=pick.team_id,
            player_name=pick.player_name,
            pick_number=pick.pick_number,
            picked_at=pick.picked_at
        ) for pick in picks
    ]

@router.post("/{draft_id}/autopick")
def trigger_autopick(
    draft_id: int,
    session: Session = Depends(get_session)
):
    """Manually trigger autopick for a draft (for testing purposes)."""
    from app.workers.draft_autopick import _perform_autopick
    
    draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.status != DraftStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Draft is not in progress")
    
    success = _perform_autopick(draft_id, session)
    if success:
        return {"message": "Autopick completed successfully"}
    else:
        raise HTTPException(status_code=400, detail="Autopick failed or not needed") 