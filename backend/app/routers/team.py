from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_session
from app.models.league_models import Team, TeamPlayer, League, LeagueMember, LeagueSettings, AgentPrediction
from app.models.player_pool_model import Players
from app.models.user_model import User
from app.models.live_data_models import PlayerStat
from app.models.match_model import Match
from app.utils.draft_utils import check_team_lock_status
from app.utils.deps import enforce_team_unlocked
from app.utils.agents import get_valid_agents, get_agent_class, FALLBACK_AGENT_TO_CLASS
from app.utils.auth import get_current_active_user
from sqlmodel import and_, or_, func

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

class TeamRenameRequest(BaseModel):
    name: str

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
    for name in body.picks:
        if name not in valid_agents:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid agent: {name}")
        normalized.append(name)
    # Note: Duplicate agents ARE allowed (player can pick same agent across multiple maps)

    # Ensure player belongs to this team
    tp = session.exec(select(TeamPlayer).where(TeamPlayer.team_id == team_id, TeamPlayer.player_name == body.player_name)).first()
    if not tp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not on this team")

    # Check if new picks include a duelist agent
    new_has_duelist = any(get_agent_class(agent, session) == "Duelist" for agent in normalized)
    
    if new_has_duelist:
        # Get team to find league settings
        team = session.exec(select(Team).where(Team.id == team_id)).first()
        if team:
            settings = session.exec(select(LeagueSettings).where(LeagueSettings.league_id == team.league_id)).first()
            max_duelist_players = settings.max_duelist_agent_players if settings else 2
            
            # Count other players on team who have duelist agents in their predictions
            all_predictions = session.exec(
                select(AgentPrediction).where(
                    AgentPrediction.team_id == team_id,
                    AgentPrediction.player_name != body.player_name  # Exclude current player
                )
            ).all()
            
            duelist_player_count = 0
            for pred in all_predictions:
                picks = [p.strip() for p in pred.picks_csv.split(",") if p.strip()]
                if any(get_agent_class(agent, session) == "Duelist" for agent in picks):
                    duelist_player_count += 1
            
            if duelist_player_count >= max_duelist_players:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot have more than {max_duelist_players} players with duelist agents. You already have {duelist_player_count}."
                )

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

@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=TeamResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
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

@router.patch("/{team_id}/rename", response_model=TeamResponse)
def rename_team(
    team_id: int,
    req: TeamRenameRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Rename a team. Only the team owner can rename their team."""
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Verify ownership
    if team.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only rename your own team"
        )
    
    # Validate name is not empty
    if not req.name or not req.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team name cannot be empty"
        )
    
    # Update the team name
    team.name = req.name.strip()
    session.add(team)
    session.commit()
    session.refresh(team)
    
    # Get player counts for response
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


# New models for player scores
class PlayerScoreInfo(BaseModel):
    player_name: str
    team: str  # Valorant team
    is_starting: bool
    total_points: float
    agent_predictions: List[str]  # 3 agent names or empty
    agent_classes: List[str]  # corresponding classes for predictions


class SwapPlayersRequest(BaseModel):
    bench_player: str   # player to promote to starter
    starter_player: str  # player to demote to bench


class SwapPlayersResponse(BaseModel):
    message: str
    promoted_player: TeamPlayerResponse
    demoted_player: TeamPlayerResponse


def _calculate_player_total_score(player_name: str, session: Session) -> float:
    """Calculate total score for a player from VCT 2026: Americas Stage 1 matches only."""
    # Only count scores from VCT 2026: Americas Stage 1
    scores = session.exec(
        select(PlayerStat.score)
        .join(Match, Match.id == PlayerStat.match_id)
        .where(
            and_(
                PlayerStat.player_name == player_name,
                PlayerStat.score.is_not(None),
                Match.match_event == "VCT 2026: Americas Stage 1"
            )
        )
    ).all()
    
    return sum(float(s) for s in scores if s is not None)


@router.get("/{team_id}/player-scores", response_model=List[PlayerScoreInfo])
def get_team_player_scores(
    team_id: int,
    session: Session = Depends(get_session)
):
    """Get all players on a team with their total scores and agent predictions."""
    # Verify team exists
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Get all players on this team
    team_players = session.exec(
        select(TeamPlayer).where(TeamPlayer.team_id == team_id)
    ).all()
    
    # Get agent predictions for this team
    predictions_raw = session.exec(
        select(AgentPrediction).where(AgentPrediction.team_id == team_id)
    ).all()
    predictions_map = {p.player_name: p for p in predictions_raw}
    
    result = []
    for tp in team_players:
        # Get player's Valorant team from Players table
        player = session.exec(
            select(Players).where(Players.player_name == tp.player_name)
        ).first()
        valorant_team = player.team if player else "Unknown"
        
        # Calculate total score
        total_points = _calculate_player_total_score(tp.player_name, session)
        
        # Get agent predictions and their classes
        agent_predictions = []
        agent_classes = []
        if tp.player_name in predictions_map:
            pred = predictions_map[tp.player_name]
            agent_predictions = [a.strip() for a in pred.picks_csv.split(",") if a.strip()]
            agent_classes = [
                get_agent_class(agent, session) or "Unknown"
                for agent in agent_predictions
            ]
        
        result.append(PlayerScoreInfo(
            player_name=tp.player_name,
            team=valorant_team,
            is_starting=tp.is_starting,
            total_points=total_points,
            agent_predictions=agent_predictions,
            agent_classes=agent_classes
        ))
    
    return result


@router.post("/{team_id}/swap-players", response_model=SwapPlayersResponse)
def swap_players(
    team_id: int,
    body: SwapPlayersRequest,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session)
):
    """Swap a bench player with a starter (promote bench player, demote starter)."""
    # Verify team exists
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found"
        )
    
    # Find the bench player
    bench_player = session.exec(
        select(TeamPlayer).where(
            TeamPlayer.team_id == team_id,
            TeamPlayer.player_name == body.bench_player
        )
    ).first()
    
    if not bench_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player '{body.bench_player}' not found on this team"
        )
    
    if bench_player.is_starting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Player '{body.bench_player}' is already a starter"
        )
    
    # Find the starter player
    starter_player = session.exec(
        select(TeamPlayer).where(
            TeamPlayer.team_id == team_id,
            TeamPlayer.player_name == body.starter_player
        )
    ).first()
    
    if not starter_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player '{body.starter_player}' not found on this team"
        )
    
    if not starter_player.is_starting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Player '{body.starter_player}' is not currently a starter"
        )
    
    # Perform the swap
    bench_player.is_starting = True
    starter_player.is_starting = False
    
    session.commit()
    session.refresh(bench_player)
    session.refresh(starter_player)
    
    # Get player details for response
    bench_player_details = session.exec(
        select(Players).where(Players.player_name == body.bench_player)
    ).first()
    starter_player_details = session.exec(
        select(Players).where(Players.player_name == body.starter_player)
    ).first()
    
    return SwapPlayersResponse(
        message=f"Successfully swapped {body.bench_player} with {body.starter_player}",
        promoted_player=TeamPlayerResponse(
            id=bench_player.id,
            player_name=bench_player.player_name,
            team=bench_player_details.team if bench_player_details else "",
            is_starting=bench_player.is_starting,
            added_at=bench_player.added_at.isoformat()
        ),
        demoted_player=TeamPlayerResponse(
            id=starter_player.id,
            player_name=starter_player.player_name,
            team=starter_player_details.team if starter_player_details else "",
            is_starting=starter_player.is_starting,
            added_at=starter_player.added_at.isoformat()
        )
    )