from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_session
from app.models.league_models import Team, TeamPlayer, League, LeagueMember, LeagueSettings, AgentPrediction
from app.models.player_pool_model import Players
from app.models.user_model import User
from app.utils.draft_utils import check_team_lock_status
from app.utils.deps import enforce_team_unlocked
from app.utils.agents import get_valid_agents

router = APIRouter(prefix="/teams", tags=["teams"])

# Pydantic models for request/response
class TeamCreate(BaseModel):
    league_id: int
    user_id: int
    name: str

class TeamResponse(BaseModel):
    id: int
    league_id: int
    user_id: int
    name: str
    created_at: str
    player_count: int
    starting_players: int
    bench_players: int

class TeamPlayerResponse(BaseModel):
    id: int
    player_name: str
    team: str  # From Players table
    is_starting: bool
    added_at: str

class AddPlayerRequest(BaseModel):
    player_name: str
    is_starting: bool = False

class SetLineupRequest(BaseModel):
    starting_players: List[str]  # List of player names
    bench_players: List[str]     # List of player names

class AgentPredictionRequest(BaseModel):
    player_name: str
    picks: List[str]  # exactly 3 agent names

class AgentPredictionResponse(BaseModel):
    team_id: int
    player_name: str
    picks: List[str]
    updated_at: str

@router.get("/user-team", response_model=TeamResponse)
def get_user_team_by_league(
    league_id: int,
    user_id: int,
    session: Session = Depends(get_session)
):
    """Get the team for a given user within a specific league"""
    team = session.exec(
        select(Team).where(
            Team.league_id == league_id,
            Team.user_id == user_id
        )
    ).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found for user in this league"
        )

    # Count players
    players = session.exec(
        select(TeamPlayer).where(TeamPlayer.team_id == team.id)
    ).all()

    starting_count = sum(1 for p in players if p.is_starting)
    bench_count = sum(1 for p in players if not p.is_starting)

    return TeamResponse(
        id=team.id,
        league_id=team.league_id,
        user_id=team.user_id,
        name=team.name,
        created_at=team.created_at.isoformat(),
        player_count=len(players),
        starting_players=starting_count,
        bench_players=bench_count
    )

@router.get("/{team_id}/agent-predictions", response_model=List[AgentPredictionResponse])
def get_agent_predictions(
    team_id: int,
    session: Session = Depends(get_session)
):
    preds = session.exec(select(AgentPrediction).where(AgentPrediction.team_id == team_id)).all()
    results: List[AgentPredictionResponse] = []
    for pred in preds:
        picks = [p.strip() for p in pred.picks_csv.split(",") if p.strip()]
        results.append(AgentPredictionResponse(
            team_id=pred.team_id,
            player_name=pred.player_name,
            picks=picks,
            updated_at=pred.updated_at.isoformat(),
        ))
    return results

@router.post("/{team_id}/agent-predictions", response_model=AgentPredictionResponse)
def set_agent_prediction(
    team_id: int,
    body: AgentPredictionRequest,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session)
):
    # Validate picks
    if not body.picks or len(body.picks) != 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide exactly 3 agents")
    
    valid_agents = get_valid_agents(session)
    normalized: List[str] = []
    seen = set()
    for name in body.picks:
        if name not in valid_agents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid agent: {name}")
        if name in seen:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate agents not allowed")
        seen.add(name)
        normalized.append(name)

    # Ensure player belongs to this team
    tp = session.exec(select(TeamPlayer).where(TeamPlayer.team_id == team_id, TeamPlayer.player_name == body.player_name)).first()
    if not tp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not on this team")

    pred = session.exec(select(AgentPrediction).where(AgentPrediction.team_id == team_id, AgentPrediction.player_name == body.player_name)).first()
    now = datetime.utcnow()
    if pred:
        pred.picks_csv = ",".join(normalized)
        pred.updated_at = now
        session.add(pred)
    else:
        pred = AgentPrediction(team_id=team_id, player_name=body.player_name, picks_csv=",".join(normalized), updated_at=now)
        session.add(pred)
    session.commit()
    return AgentPredictionResponse(team_id=team_id, player_name=body.player_name, picks=normalized, updated_at=now.isoformat())

@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team_data: TeamCreate,
    session: Session = Depends(get_session)
):
    """Create a new team"""
    # Check if league exists
    league = session.exec(select(League).where(League.id == team_data.league_id)).first()
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="League not found"
        )
    
    # Check if user is a member of the league
    member = session.exec(
        select(LeagueMember).where(
            LeagueMember.league_id == team_data.league_id,
            LeagueMember.user_id == team_data.user_id
        )
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a member of this league"
        )
    
    # Check if user already has a team in this league
    existing_team = session.exec(
        select(Team).where(
            Team.league_id == team_data.league_id,
            Team.user_id == team_data.user_id
        )
    ).first()
    
    if existing_team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a team in this league"
        )
    
    # Create team
    team = Team(
        league_id=team_data.league_id,
        user_id=team_data.user_id,
        name=team_data.name
    )
    session.add(team)
    session.commit()
    session.refresh(team)
    
    return TeamResponse(
        id=team.id,
        league_id=team.league_id,
        user_id=team.user_id,
        name=team.name,
        created_at=team.created_at.isoformat(),
        player_count=0,
        starting_players=0,
        bench_players=0
    )

@router.get("/{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    session: Session = Depends(get_session)
):
    """Get a specific team by ID"""
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Count players
    players = session.exec(
        select(TeamPlayer).where(TeamPlayer.team_id == team_id)
    ).all()
    
    starting_count = sum(1 for p in players if p.is_starting)
    bench_count = sum(1 for p in players if not p.is_starting)
    
    return TeamResponse(
        id=team.id,
        league_id=team.league_id,
        user_id=team.user_id,
        name=team.name,
        created_at=team.created_at.isoformat(),
        player_count=len(players),
        starting_players=starting_count,
        bench_players=bench_count
    )

@router.get("/{team_id}/players", response_model=List[TeamPlayerResponse])
def get_team_players(
    team_id: int,
    session: Session = Depends(get_session)
):
    """Get all players on a team"""
    team_players = session.exec(
        select(TeamPlayer).where(TeamPlayer.team_id == team_id)
    ).all()
    
    result = []
    for tp in team_players:
        # Get player details from Players table
        player = session.exec(
            select(Players).where(Players.player_name == tp.player_name)
        ).first()
        
        result.append(TeamPlayerResponse(
            id=tp.id,
            player_name=tp.player_name,
            team=player.team if player else "Unknown",
            is_starting=tp.is_starting,
            added_at=tp.added_at.isoformat()
        ))
    
    return result

 

@router.post("/{team_id}/players", response_model=TeamPlayerResponse)
def add_player_to_team(
    team_id: int,
    player_data: AddPlayerRequest,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session)
):
    """Add a player to a team"""
    # Roster lock enforced by dependency
    
    # Check if team exists
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Check if player exists in player pool
    player = session.exec(
        select(Players).where(Players.player_name == player_data.player_name)
    ).first()
    
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found in player pool"
        )
    
    # Check if player is already on this team
    existing_player = session.exec(
        select(TeamPlayer).where(
            TeamPlayer.team_id == team_id,
            TeamPlayer.player_name == player_data.player_name
        )
    ).first()
    
    if existing_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player is already on this team"
        )
    
    # Get league settings to check roster limits
    settings = session.exec(
        select(LeagueSettings).where(LeagueSettings.league_id == team.league_id)
    ).first()
    
    # Count current players
    current_players = len(session.exec(
        select(TeamPlayer).where(TeamPlayer.team_id == team_id)
    ).all())
    
    if current_players >= settings.max_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team already has maximum number of players ({settings.max_players})"
        )
    
    # Add player to team
    team_player = TeamPlayer(
        team_id=team_id,
        player_name=player_data.player_name,
        is_starting=player_data.is_starting
    )
    session.add(team_player)
    session.commit()
    session.refresh(team_player)
    
    return TeamPlayerResponse(
        id=team_player.id,
        player_name=team_player.player_name,
        team=player.team,
        is_starting=team_player.is_starting,
        added_at=team_player.added_at.isoformat()
    )

@router.delete("/{team_id}/players/{player_name}")
def remove_player_from_team(
    team_id: int,
    player_name: str,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session)
):
    """Remove a player from a team"""
    # Roster lock enforced by dependency
    # Check if player is on the team
    team_player = session.exec(
        select(TeamPlayer).where(
            TeamPlayer.team_id == team_id,
            TeamPlayer.player_name == player_name
        )
    ).first()
    
    if not team_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found on this team"
        )
    
    session.delete(team_player)
    session.commit()
    
    return {"message": "Player removed from team"}

@router.put("/{team_id}/lineup")
def set_team_lineup(
    team_id: int,
    lineup_data: SetLineupRequest,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session)
):
    """Set the starting lineup for a team"""
    # Roster lock enforced by dependency
    
    # Check if team exists
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Get league settings
    settings = session.exec(
        select(LeagueSettings).where(LeagueSettings.league_id == team.league_id)
    ).first()
    
    # Validate lineup size
    if len(lineup_data.starting_players) != settings.starting_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Must have exactly {settings.starting_players} starting players"
        )
    
    if len(lineup_data.bench_players) != settings.bench_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Must have exactly {settings.bench_players} bench players"
        )
    
    # Get all players on the team
    team_players = session.exec(
        select(TeamPlayer).where(TeamPlayer.team_id == team_id)
    ).all()

    # Create a set of current team player names for validation
    current_player_names = {tp.player_name for tp in team_players}

    # Validate that all specified players are actually on the team
    all_specified_players = set(lineup_data.starting_players + lineup_data.bench_players)
    invalid_players = all_specified_players - current_player_names

    if invalid_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The following players are not on this team: {', '.join(sorted(invalid_players))}"
        )

    # Validate that all current team players are accounted for in the lineup
    missing_players = current_player_names - all_specified_players

    if missing_players:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The following team players are missing from the lineup: {', '.join(sorted(missing_players))}"
        )

    # Update lineup - now we know all players are valid
    for tp in team_players:
        if tp.player_name in lineup_data.starting_players:
            tp.is_starting = True
        elif tp.player_name in lineup_data.bench_players:
            tp.is_starting = False
    
    session.commit()
    
    return {"message": "Lineup updated successfully"}

@router.patch("/{team_id}/players/{player_name}/toggle-starter")
def toggle_player_starting_status(
    team_id: int,
    player_name: str,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session)
):
    """Toggle a player's starting status (starter ↔ bench)"""
    # Roster lock enforced by dependency
    
    # Check if team exists
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Find the player on the team
    team_player = session.exec(
        select(TeamPlayer).where(
            TeamPlayer.team_id == team_id,
            TeamPlayer.player_name == player_name
        )
    ).first()
    
    if not team_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found on this team"
        )
    
    # Get league settings to validate starter limits
    settings = session.exec(
        select(LeagueSettings).where(LeagueSettings.league_id == team.league_id)
    ).first()
    
    # If moving from bench to starter, check starter limit
    if not team_player.is_starting:
        # Count current starters
        current_starters = session.exec(
            select(TeamPlayer).where(
                TeamPlayer.team_id == team_id,
                TeamPlayer.is_starting == True
            )
        ).all()
        
        if len(current_starters) >= settings.starting_players:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team already has maximum number of starters ({settings.starting_players})"
            )
    
    # Toggle the starting status
    team_player.is_starting = not team_player.is_starting
    session.commit()
    session.refresh(team_player)
    
    # Get player details for response
    player = session.exec(
        select(Players).where(Players.player_name == player_name)
    ).first()
    
    return TeamPlayerResponse(
        id=team_player.id,
        player_name=team_player.player_name,
        team=player.team if player else "",
        is_starting=team_player.is_starting,
        added_at=team_player.added_at.isoformat()
    )

@router.get("/{team_id}/lock-status")
def get_team_lock_status(
    team_id: int,
    session: Session = Depends(get_session)
):
    """Check if team changes are currently locked based on weekly schedule."""
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    is_locked, message, next_time = check_team_lock_status(session)
    return {
        "team_id": team_id,
        "is_locked": is_locked,
        "message": message,
        "next_match_time": next_time.isoformat() if next_time else None,
        "lock_reason": "weekly_schedule" if is_locked else None,
    }