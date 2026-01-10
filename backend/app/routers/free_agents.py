from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database import get_session
from app.models.league_models import League, Team, TeamPlayer, FreeAgentTransaction
from app.models.player_pool_model import Players
from app.utils.draft_utils import (
    get_free_agents_for_league, 
    validate_free_agent_swap,
    perform_free_agent_swap,
)
from app.utils.deps import enforce_team_unlocked
from app.utils.auth import get_current_user

router = APIRouter(prefix="/free-agents", tags=["free-agents"])

class FreeAgentResponse(BaseModel):
    player_name: str
    team: str
    image_url: str | None

class FreeAgentSwapRequest(BaseModel):
    team_id: int
    drop_player_name: str
    add_player_name: str

class FreeAgentSwapResponse(BaseModel):
    success: bool
    message: str
    dropped_player: str
    added_player: str
    transaction_date: datetime

class FreeAgentTransactionResponse(BaseModel):
    id: int
    team_id: int
    player_name: str
    transaction_type: str
    transaction_date: datetime

class FreeAgentAddRequest(BaseModel):
    team_id: int
    add_player_name: str

class FreeAgentAddResponse(BaseModel):
    success: bool
    message: str
    added_player: str
    transaction_date: datetime

class FreeAgentDropRequest(BaseModel):
    team_id: int
    drop_player_name: str

class FreeAgentDropResponse(BaseModel):
    success: bool
    message: str
    dropped_player: str
    transaction_date: datetime

@router.get("/{league_id}/pool", response_model=List[FreeAgentResponse])
def get_free_agent_pool(
    league_id: int,
    session: Session = Depends(get_session)
):
    """Get all available free agents for a league."""
    # Verify league exists
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Get free agents
    free_agents = get_free_agents_for_league(session, league_id)
    
    return [
        FreeAgentResponse(
            player_name=player.player_name,
            team=player.team,
            image_url=player.image_url
        ) for player in free_agents
    ]

@router.post("/{league_id}/add", response_model=FreeAgentAddResponse)
def add_free_agent(
    league_id: int,
    req: FreeAgentAddRequest,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    """Add a free agent to a team without requiring a drop (roster size will be enforced at lock)."""
    # Roster lock enforced by dependency
    # Verify league and team
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    team = session.exec(select(Team).where(Team.id == req.team_id)).first()
    if not team or team.league_id != league_id:
        raise HTTPException(status_code=400, detail="Team not found in this league")
    if team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this team")

    # Ensure player is available as free agent
    free_agents = get_free_agents_for_league(session, league_id)
    fa_names = {p.player_name for p in free_agents}
    if req.add_player_name not in fa_names:
        raise HTTPException(status_code=400, detail=f"Player {req.add_player_name} is not available as a free agent")

    # Note: Duelist player role restriction removed - only agent prediction duelist limit applies now

    # Add to team roster
    team_player = TeamPlayer(team_id=req.team_id, player_name=req.add_player_name, is_starting=False)
    session.add(team_player)
    # Record transaction
    tx = FreeAgentTransaction(
        league_id=league_id,
        team_id=req.team_id,
        player_name=req.add_player_name,
        transaction_type="add",
        transaction_date=datetime.now()
    )
    session.add(tx)
    session.commit()
    return FreeAgentAddResponse(success=True, message=f"Added {req.add_player_name}", added_player=req.add_player_name, transaction_date=tx.transaction_date)

@router.post("/{league_id}/drop", response_model=FreeAgentDropResponse)
def drop_player(
    league_id: int,
    req: FreeAgentDropRequest,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    """Drop a player from a team without requiring an add (roster size will be enforced at lock)."""
    # Roster lock enforced by dependency
    # Verify league and team
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    team = session.exec(select(Team).where(Team.id == req.team_id)).first()
    if not team or team.league_id != league_id:
        raise HTTPException(status_code=400, detail="Team not found in this league")
    if team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this team")

    # Ensure player on team
    team_player = session.exec(select(TeamPlayer).where(TeamPlayer.team_id == req.team_id, TeamPlayer.player_name == req.drop_player_name)).first()
    if not team_player:
        raise HTTPException(status_code=404, detail="Player not on team")

    session.delete(team_player)
    # Record transaction
    tx = FreeAgentTransaction(
        league_id=league_id,
        team_id=req.team_id,
        player_name=req.drop_player_name,
        transaction_type="drop",
        transaction_date=datetime.now()
    )
    session.add(tx)
    session.commit()
    return FreeAgentDropResponse(success=True, message=f"Dropped {req.drop_player_name}", dropped_player=req.drop_player_name, transaction_date=tx.transaction_date)

@router.post("/{league_id}/swap", response_model=FreeAgentSwapResponse)
def make_free_agent_swap(
    league_id: int,
    req: FreeAgentSwapRequest,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session),
    current_user = Depends(get_current_user),
):
    """Swap a player from your team with a free agent."""
    # Roster lock enforced by dependency
    
    # Verify league exists
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Verify team exists and is in this league
    team = session.exec(select(Team).where(Team.id == req.team_id)).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.league_id != league_id:
        raise HTTPException(status_code=400, detail="Team is not in this league")
    if team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this team")
    
    # Check if the player being added is actually a free agent
    free_agents = get_free_agents_for_league(session, league_id)
    free_agent_names = {player.player_name for player in free_agents}
    
    if req.add_player_name not in free_agent_names:
        raise HTTPException(
            status_code=400, 
            detail=f"Player {req.add_player_name} is not available as a free agent"
        )
    
    # Validate the swap (including duelist restrictions)
    is_valid, error_message = validate_free_agent_swap(
        session, req.team_id, req.drop_player_name, req.add_player_name
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_message)
    
    # Perform the swap
    try:
        perform_free_agent_swap(
            session, req.team_id, league_id, req.drop_player_name, req.add_player_name
        )
        session.commit()
        
        return FreeAgentSwapResponse(
            success=True,
            message=f"Successfully swapped {req.drop_player_name} for {req.add_player_name}",
            dropped_player=req.drop_player_name,
            added_player=req.add_player_name,
            transaction_date=datetime.now()
        )
        
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to complete swap: {str(e)}"
        )

@router.get("/{league_id}/transactions", response_model=List[FreeAgentTransactionResponse])
def get_league_transactions(
    league_id: int,
    session: Session = Depends(get_session)
):
    """Get all free agent transactions for a league."""
    # Verify league exists
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Get transactions
    transactions = session.exec(
        select(FreeAgentTransaction)
        .where(FreeAgentTransaction.league_id == league_id)
        .order_by(FreeAgentTransaction.transaction_date.desc())
    ).all()
    
    return [
        FreeAgentTransactionResponse(
            id=tx.id,
            team_id=tx.team_id,
            player_name=tx.player_name,
            transaction_type=tx.transaction_type,
            transaction_date=tx.transaction_date
        ) for tx in transactions
    ]

@router.get("/{league_id}/team/{team_id}/transactions", response_model=List[FreeAgentTransactionResponse])
def get_team_transactions(
    league_id: int,
    team_id: int,
    session: Session = Depends(get_session)
):
    """Get all free agent transactions for a specific team."""
    # Verify league and team exist
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if team.league_id != league_id:
        raise HTTPException(status_code=400, detail="Team is not in this league")
    
    # Get team transactions
    transactions = session.exec(
        select(FreeAgentTransaction)
        .where(
            FreeAgentTransaction.league_id == league_id,
            FreeAgentTransaction.team_id == team_id
        )
        .order_by(FreeAgentTransaction.transaction_date.desc())
    ).all()
    
    return [
        FreeAgentTransactionResponse(
            id=tx.id,
            team_id=tx.team_id,
            player_name=tx.player_name,
            transaction_type=tx.transaction_type,
            transaction_date=tx.transaction_date
        ) for tx in transactions
    ]