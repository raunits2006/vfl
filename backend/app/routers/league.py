from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
import secrets
import string
from pydantic import BaseModel

from app.database import get_session
from app.models.league_models import League, LeagueMember, LeagueSettings, LeagueStatus, Team
from app.models.user_model import User
from app.utils.auth import get_current_active_user

router = APIRouter(prefix="/leagues", tags=["leagues"])

# Pydantic models for request/response
class LeagueCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_teams: int = 8
    creator_user_id: Optional[int] = None

class LeagueResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    max_teams: int
    status: LeagueStatus
    created_at: str
    member_count: int

class LeagueJoin(BaseModel):
    user_id: int
    pin: Optional[str] = None

class UserLeaguesRequest(BaseModel):
    user_id: int

class LeagueMemberInfo(BaseModel):
    user_id: int
    username: str
    is_commissioner: bool
    joined_at: str

class LeagueDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    max_teams: int
    status: LeagueStatus
    created_at: str
    member_count: int
    join_pin: Optional[str]
    members: List[LeagueMemberInfo]

class LeagueSettingsResponse(BaseModel):
    max_players: int
    starting_players: int
    bench_players: int
    points_per_kill: float
    points_per_assist: float
    use_best_2_of_3: bool
    draft_type: str
    agent_exact_match_multiplier: float
    agent_class_match_multiplier: float
    agent_miss_multiplier: float

class LeagueSettingsUpdate(BaseModel):
    max_players: Optional[int] = None
    starting_players: Optional[int] = None
    bench_players: Optional[int] = None
    points_per_kill: Optional[float] = None
    points_per_assist: Optional[float] = None
    use_best_2_of_3: Optional[bool] = None
    draft_type: Optional[str] = None
    agent_exact_match_multiplier: Optional[float] = None
    agent_class_match_multiplier: Optional[float] = None
    agent_miss_multiplier: Optional[float] = None

class JoinByPinRequest(BaseModel):
    user_id: int
    pin: str

def create_team_for_user(session: Session, league_id: int, user_id: int, username: Optional[str] = None) -> Team:
    """Create a team for a user in a league if it doesn't exist, and return it."""
    existing_team = session.exec(
        select(Team).where(
            Team.league_id == league_id,
            Team.user_id == user_id
        )
    ).first()
    if existing_team:
        return existing_team

    if not username:
        user = session.exec(select(User).where(User.id == user_id)).first()
        username = user.username if user else "User"

    team_name = f"{username}'s Team"
    team = Team(
        league_id=league_id,
        user_id=user_id,
        name=team_name
    )
    session.add(team)
    session.commit()
    session.refresh(team)
    return team

@router.post("", response_model=LeagueResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=LeagueResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_league(
    league_data: LeagueCreate,
    session: Session = Depends(get_session)
):
    """Create a new league"""
    # Create league
    # Generate a 6-digit PIN code
    pin = ''.join(secrets.choice(string.digits) for _ in range(6))
    league = League(
        name=league_data.name,
        description=league_data.description,
        max_teams=league_data.max_teams,
        join_pin=pin
    )
    session.add(league)
    session.commit()
    session.refresh(league)
    
    # Create default league settings
    settings = LeagueSettings(league_id=league.id)
    session.add(settings)
    session.commit()

    # If creator_user_id is provided, add as first member (commissioner)
    if league_data.creator_user_id is not None:
        creator = session.exec(select(User).where(User.id == league_data.creator_user_id)).first()
        if creator:
            # Ensure not already a member (shouldn't be right after creation)
            existing_member = session.exec(
                select(LeagueMember).where(
                    LeagueMember.league_id == league.id,
                    LeagueMember.user_id == league_data.creator_user_id
                )
            ).first()
            if not existing_member:
                commissioner_member = LeagueMember(
                    league_id=league.id,
                    user_id=league_data.creator_user_id,
                    is_commissioner=True
                )
                session.add(commissioner_member)
                session.commit()
                
                # Auto-create team for creator
                create_team_for_user(session, league.id, league_data.creator_user_id, creator.username)
    
    return LeagueResponse(
        id=league.id,
        name=league.name,
        description=league.description,
        max_teams=league.max_teams,
        status=league.status,
        created_at=league.created_at.isoformat(),
        member_count=len(session.exec(select(LeagueMember).where(LeagueMember.league_id == league.id)).all())
    )

@router.get("", response_model=List[LeagueResponse])
@router.get("/", response_model=List[LeagueResponse], include_in_schema=False)
def get_leagues(
    session: Session = Depends(get_session),
    skip: int = 0,
    limit: int = 100
):
    """Get all leagues"""
    leagues = session.exec(select(League).offset(skip).limit(limit)).all()
    
    result = []
    for league in leagues:
        # Count members
        members = session.exec(
            select(LeagueMember).where(LeagueMember.league_id == league.id)
        ).all()
        member_count = len(members)
        
        result.append(LeagueResponse(
            id=league.id,
            name=league.name,
            description=league.description,
            max_teams=league.max_teams,
            status=league.status,
            created_at=league.created_at.isoformat(),
            member_count=member_count
        ))
    
    return result

@router.get("/{league_id}", response_model=LeagueResponse)
def get_league(
    league_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific league by ID.
    
    Returns 403 for both non-existent leagues and non-member access
    to prevent league enumeration attacks.
    """
    league = session.exec(select(League).where(League.id == league_id)).first()
    
    # Check membership (also handles non-existent leagues)
    membership = None
    if league:
        membership = session.exec(
            select(LeagueMember).where(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id
            )
        ).first()
    
    # Return same error for both cases to prevent information leakage
    if not league or not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Count members
    members = session.exec(
        select(LeagueMember).where(LeagueMember.league_id == league.id)
    ).all()
    member_count = len(members)
    
    return LeagueResponse(
        id=league.id,
        name=league.name,
        description=league.description,
        max_teams=league.max_teams,
        status=league.status,
        created_at=league.created_at.isoformat(),
        member_count=member_count
    )

@router.get("/{league_id}/details", response_model=LeagueDetailResponse)
def get_league_details(
    league_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get league details including members and join PIN.
    
    Returns 403 for both non-existent leagues and non-member access
    to prevent league enumeration attacks.
    """
    league = session.exec(select(League).where(League.id == league_id)).first()
    
    # Check membership (also handles non-existent leagues)
    membership = None
    if league:
        membership = session.exec(
            select(LeagueMember).where(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id
            )
        ).first()
    
    # Return same error for both cases to prevent information leakage
    if not league or not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    members = session.exec(select(LeagueMember).where(LeagueMember.league_id == league_id)).all()
    member_infos: List[LeagueMemberInfo] = []
    for m in members:
        u = session.exec(select(User).where(User.id == m.user_id)).first()
        member_infos.append(LeagueMemberInfo(
            user_id=m.user_id,
            username=u.username if u else "Unknown",
            is_commissioner=m.is_commissioner,
            joined_at=m.joined_at.isoformat(),
        ))

    return LeagueDetailResponse(
        id=league.id,
        name=league.name,
        description=league.description,
        max_teams=league.max_teams,
        status=league.status,
        created_at=league.created_at.isoformat(),
        member_count=len(members),
        join_pin=league.join_pin,
        members=member_infos,
    )

@router.get("/{league_id}/settings", response_model=LeagueSettingsResponse)
def get_league_settings(
    league_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get league settings (roster, scoring, draft type).
    
    Returns 403 for both non-existent leagues and non-member access
    to prevent league enumeration attacks.
    """
    league = session.exec(select(League).where(League.id == league_id)).first()
    
    # Check membership (also handles non-existent leagues)
    membership = None
    if league:
        membership = session.exec(
            select(LeagueMember).where(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id
            )
        ).first()
    
    # Return same error for both cases to prevent information leakage
    if not league or not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    settings = session.exec(select(LeagueSettings).where(LeagueSettings.league_id == league_id)).first()
    if not settings:
        # Create defaults if somehow missing
        settings = LeagueSettings(league_id=league_id)
        session.add(settings)
        session.commit()
        session.refresh(settings)

    return LeagueSettingsResponse(
        max_players=settings.max_players,
        starting_players=settings.starting_players,
        bench_players=settings.bench_players,
        points_per_kill=settings.points_per_kill,
        points_per_assist=settings.points_per_assist,
        use_best_2_of_3=settings.use_best_2_of_3,
        draft_type=settings.draft_type,
        agent_exact_match_multiplier=settings.agent_exact_match_multiplier,
        agent_class_match_multiplier=settings.agent_class_match_multiplier,
        agent_miss_multiplier=settings.agent_miss_multiplier,
    )

@router.put("/{league_id}/settings", response_model=LeagueSettingsResponse)
def update_league_settings(
    league_id: int,
    payload: LeagueSettingsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Update league settings. Only the league commissioner may update settings.

    If roster sizes are updated, enforces that starting_players + bench_players equals max_players.
    Returns 403 for both non-existent leagues and non-commissioner access.
    """
    league = session.exec(select(League).where(League.id == league_id)).first()
    
    # Verify current user is the commissioner of this league
    membership = None
    if league:
        membership = session.exec(
            select(LeagueMember).where(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id
            )
        ).first()
    
    if not league or not membership or not membership.is_commissioner:
        raise HTTPException(status_code=403, detail="Access denied")

    settings = session.exec(select(LeagueSettings).where(LeagueSettings.league_id == league_id)).first()
    if not settings:
        settings = LeagueSettings(league_id=league_id)
        session.add(settings)
        session.commit()
        session.refresh(settings)

    # Prepare prospective values to validate constraints
    new_max = payload.max_players if payload.max_players is not None else settings.max_players
    new_start = payload.starting_players if payload.starting_players is not None else settings.starting_players
    new_bench = payload.bench_players if payload.bench_players is not None else settings.bench_players

    # Basic validation
    if new_max <= 0 or new_start < 0 or new_bench < 0:
        raise HTTPException(status_code=400, detail="Invalid roster values")
    if new_start + new_bench != new_max:
        raise HTTPException(status_code=400, detail="starting_players + bench_players must equal max_players")

    # Multiplier validation (non-negative)
    if payload.agent_exact_match_multiplier is not None and payload.agent_exact_match_multiplier < 0:
        raise HTTPException(status_code=400, detail="agent_exact_match_multiplier cannot be negative")
    if payload.agent_class_match_multiplier is not None and payload.agent_class_match_multiplier < 0:
        raise HTTPException(status_code=400, detail="agent_class_match_multiplier cannot be negative")
    if payload.agent_miss_multiplier is not None and payload.agent_miss_multiplier < 0:
        raise HTTPException(status_code=400, detail="agent_miss_multiplier cannot be negative")

    # Apply updates
    if payload.max_players is not None:
        settings.max_players = payload.max_players
    if payload.starting_players is not None:
        settings.starting_players = payload.starting_players
    if payload.bench_players is not None:
        settings.bench_players = payload.bench_players
    if payload.points_per_kill is not None:
        settings.points_per_kill = payload.points_per_kill
    if payload.points_per_assist is not None:
        settings.points_per_assist = payload.points_per_assist
    if payload.use_best_2_of_3 is not None:
        settings.use_best_2_of_3 = payload.use_best_2_of_3
    if payload.draft_type is not None:
        settings.draft_type = payload.draft_type
    if payload.agent_exact_match_multiplier is not None:
        settings.agent_exact_match_multiplier = payload.agent_exact_match_multiplier
    if payload.agent_class_match_multiplier is not None:
        settings.agent_class_match_multiplier = payload.agent_class_match_multiplier
    if payload.agent_miss_multiplier is not None:
        settings.agent_miss_multiplier = payload.agent_miss_multiplier

    session.add(settings)
    session.commit()
    session.refresh(settings)

    return LeagueSettingsResponse(
        max_players=settings.max_players,
        starting_players=settings.starting_players,
        bench_players=settings.bench_players,
        points_per_kill=settings.points_per_kill,
        points_per_assist=settings.points_per_assist,
        use_best_2_of_3=settings.use_best_2_of_3,
        draft_type=settings.draft_type,
        agent_exact_match_multiplier=settings.agent_exact_match_multiplier,
        agent_class_match_multiplier=settings.agent_class_match_multiplier,
        agent_miss_multiplier=settings.agent_miss_multiplier,
    )

# Commissioner management
class SetCommissionerRequest(BaseModel):
    is_commissioner: bool

@router.put("/{league_id}/members/{member_user_id}/commissioner")
def set_commissioner_status(
    league_id: int,
    member_user_id: int,
    req: SetCommissionerRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Assign or remove commissioner status for a league member. Only current commissioners may change roles.

    Prevent removing the last remaining commissioner.
    Returns 403 for both non-existent leagues and non-commissioner access.
    """
    league = session.exec(select(League).where(League.id == league_id)).first()
    
    # Requester must be a commissioner
    requester_membership = None
    if league:
        requester_membership = session.exec(
            select(LeagueMember).where(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id
            )
        ).first()
    
    if not league or not requester_membership or not requester_membership.is_commissioner:
        raise HTTPException(status_code=403, detail="Access denied")

    target_membership = session.exec(
        select(LeagueMember).where(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == member_user_id
        )
    ).first()
    if not target_membership:
        raise HTTPException(status_code=404, detail="Member not found in league")

    # If demoting, ensure not removing last commissioner
    if target_membership.is_commissioner and not req.is_commissioner:
        num_commissioners = session.exec(
            select(LeagueMember).where(
                LeagueMember.league_id == league_id,
                LeagueMember.is_commissioner == True
            )
        ).all()
        if len(num_commissioners) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last commissioner")

    target_membership.is_commissioner = req.is_commissioner
    session.add(target_membership)
    session.commit()
    return {"user_id": member_user_id, "is_commissioner": target_membership.is_commissioner}

@router.post("/{league_id}/regenerate-pin")
def regenerate_join_pin(
    league_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Generate a new 6-digit join PIN for the league.
    
    Returns 403 for both non-existent leagues and non-commissioner access.
    """
    league = session.exec(select(League).where(League.id == league_id)).first()
    
    # Verify current user is a commissioner
    membership = None
    if league:
        membership = session.exec(
            select(LeagueMember).where(
                LeagueMember.league_id == league_id,
                LeagueMember.user_id == current_user.id
            )
        ).first()
    
    if not league or not membership or not membership.is_commissioner:
        raise HTTPException(status_code=403, detail="Access denied")

    league.join_pin = ''.join(secrets.choice(string.digits) for _ in range(6))
    session.add(league)
    session.commit()
    return {"join_pin": league.join_pin}

@router.get("/user/{user_id}", response_model=List[LeagueResponse])
def get_user_leagues(
    user_id: int,
    session: Session = Depends(get_session)
):
    """Get leagues that a specific user is a member of."""
    memberships = session.exec(select(LeagueMember).where(LeagueMember.user_id == user_id)).all()
    league_ids = [m.league_id for m in memberships]
    if not league_ids:
        return []

    leagues = session.exec(select(League).where(League.id.in_(league_ids))).all()
    result = []
    for league in leagues:
        member_count = len(session.exec(
            select(LeagueMember).where(LeagueMember.league_id == league.id)
        ).all())
        result.append(LeagueResponse(
            id=league.id,
            name=league.name,
            description=league.description,
            max_teams=league.max_teams,
            status=league.status,
            created_at=league.created_at.isoformat(),
            member_count=member_count
        ))
    return result

@router.post("/join-by-pin")
def join_league_by_pin(
    body: JoinByPinRequest,
    session: Session = Depends(get_session)
):
    """Join a league using a 6-digit PIN."""
    league = session.exec(select(League).where(League.join_pin == body.pin)).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid PIN"
        )

    # Reuse join_league validations
    # Check if user exists
    user = session.exec(select(User).where(User.id == body.user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    existing_member = session.exec(
        select(LeagueMember).where(
            LeagueMember.league_id == league.id,
            LeagueMember.user_id == body.user_id
        )
    ).first()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this league"
        )

    current_members = session.exec(
        select(LeagueMember).where(LeagueMember.league_id == league.id)
    ).all()
    if len(current_members) >= league.max_teams:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="League is full"
        )

    member = LeagueMember(
        league_id=league.id,
        user_id=body.user_id,
        is_commissioner=(len(current_members) == 0)
    )
    session.add(member)
    session.commit()

    # Auto-create team for the joining user
    create_team_for_user(session, league.id, body.user_id, user.username)

    return {"message": "Successfully joined league", "league_id": league.id}

@router.post("/{league_id}/join", status_code=status.HTTP_200_OK)
def join_league(
    league_id: int,
    join_data: LeagueJoin,
    session: Session = Depends(get_session)
):
    """Join a league"""
    # Check if league exists
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )
    
    # Check if user exists
    user = session.exec(select(User).where(User.id == join_data.user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is already a member
    existing_member = session.exec(
        select(LeagueMember).where(
            LeagueMember.league_id == league_id,
            LeagueMember.user_id == join_data.user_id
        )
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this league"
        )
    
    # Check if league is full
    current_members = session.exec(
        select(LeagueMember).where(LeagueMember.league_id == league_id)
    ).all()
    current_member_count = len(current_members)
    # PIN validation
    if league.join_pin is not None:
        # League requires PIN
        if join_data.pin is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This league requires a PIN to join"
            )
        if join_data.pin != league.join_pin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PIN"
            )

    # Add member
    member = LeagueMember(
        league_id=league_id,
        user_id=join_data.user_id,
        is_commissioner=(current_member_count == 0)  # First member becomes commissioner
    )
    session.add(member)
    session.commit()

    # Auto-create team for the joining user
    create_team_for_user(session, league_id, join_data.user_id, user.username)
    
    return {"message": "Successfully joined league"}