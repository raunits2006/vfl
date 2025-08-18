"""
Trade system router for proposing, accepting, and rejecting player trades between teams.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_session
from app.models.league_models import (
    Trade, TradeItem, TradeStatus, League, Team, TeamPlayer, LeagueSettings
)
from app.models.user_model import User
from app.utils.auth import get_current_active_user
from app.utils.deps import enforce_team_unlocked

router = APIRouter(prefix="/trades", tags=["trades"])

import logging

# WebSocket broadcast functions removed - using polling instead for trades

# Pydantic models for request/response
class TradePlayerRequest(BaseModel):
    player_name: str

class ProposeTradeRequest(BaseModel):
    offering_team_id: int
    receiving_team_id: int
    offering_players: List[str]  # List of player names
    receiving_players: List[str]  # List of player names

class TradeResponse(BaseModel):
    id: int
    league_id: int
    team1_id: int
    team2_id: int
    status: TradeStatus
    proposed_at: datetime
    responded_at: Optional[datetime]
    offering_players: List[str]
    receiving_players: List[str]

class TradeDetailResponse(BaseModel):
    id: int
    league_id: int
    team1_id: int
    team1_name: str
    team2_id: int
    team2_name: str
    status: TradeStatus
    proposed_at: datetime
    responded_at: Optional[datetime]
    trade_items: List[dict]

@router.post("/{league_id}/propose", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
def propose_trade(
    league_id: int,
    trade_data: ProposeTradeRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Propose a trade between two teams in a league."""
    # Roster lock enforced by dependency
    
    # Verify league exists
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Verify teams exist and are in the league
    offering_team = session.exec(select(Team).where(Team.id == trade_data.offering_team_id)).first()
    receiving_team = session.exec(select(Team).where(Team.id == trade_data.receiving_team_id)).first()
    
    if not offering_team or offering_team.league_id != league_id:
        raise HTTPException(status_code=400, detail="Offering team not found in this league")
    
    if not receiving_team or receiving_team.league_id != league_id:
        raise HTTPException(status_code=400, detail="Receiving team not found in this league")
    
    # Verify current user owns the offering team
    if offering_team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only propose trades for your own team")
    
    # Cannot trade with yourself
    if trade_data.offering_team_id == trade_data.receiving_team_id:
        raise HTTPException(status_code=400, detail="Cannot trade with your own team")
    
    # Validate trade requirements (uneven trades allowed)
    if not trade_data.offering_players or not trade_data.receiving_players:
        raise HTTPException(status_code=400, detail="Both teams must offer at least one player")
    
    # Verify all offered players are on the offering team
    offering_team_players = session.exec(
        select(TeamPlayer).where(TeamPlayer.team_id == trade_data.offering_team_id)
    ).all()
    offering_player_names = {tp.player_name for tp in offering_team_players}
    
    for player_name in trade_data.offering_players:
        if player_name not in offering_player_names:
            raise HTTPException(
                status_code=400, 
                detail=f"Player {player_name} is not on the offering team"
            )
    
    # Verify all requested players are on the receiving team
    receiving_team_players = session.exec(
        select(TeamPlayer).where(TeamPlayer.team_id == trade_data.receiving_team_id)
    ).all()
    receiving_player_names = {tp.player_name for tp in receiving_team_players}
    
    for player_name in trade_data.receiving_players:
        if player_name not in receiving_player_names:
            raise HTTPException(
                status_code=400, 
                detail=f"Player {player_name} is not on the receiving team"
            )
    
    # Create trade
    trade = Trade(
        league_id=league_id,
        team1_id=trade_data.offering_team_id,
        team2_id=trade_data.receiving_team_id,
        status=TradeStatus.PENDING
    )
    session.add(trade)
    session.commit()
    session.refresh(trade)
    
    # Create trade items for offering players
    for player_name in trade_data.offering_players:
        trade_item = TradeItem(
            trade_id=trade.id,
            team_id=trade_data.offering_team_id,
            player_name=player_name
        )
        session.add(trade_item)
    
    # Create trade items for receiving players
    for player_name in trade_data.receiving_players:
        trade_item = TradeItem(
            trade_id=trade.id,
            team_id=trade_data.receiving_team_id,
            player_name=player_name
        )
        session.add(trade_item)
    
    session.commit()
    
    # Trade proposal created - clients will poll for updates
    
    return TradeResponse(
        id=trade.id,
        league_id=trade.league_id,
        team1_id=trade.team1_id,
        team2_id=trade.team2_id,
        status=trade.status,
        proposed_at=trade.proposed_at,
        responded_at=trade.responded_at,
        offering_players=trade_data.offering_players,
        receiving_players=trade_data.receiving_players
    )

@router.get("/{league_id}", response_model=List[TradeDetailResponse])
def get_league_trades(
    league_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get all trades for a league."""
    # Verify league exists
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    
    # Get all trades for the league
    trades = session.exec(
        select(Trade).where(Trade.league_id == league_id).order_by(Trade.proposed_at.desc())
    ).all()

    # Fetch teams and trade items in bulk to avoid N+1 queries
    team_ids: set[int] = set()
    for t in trades:
        team_ids.add(t.team1_id)
        team_ids.add(t.team2_id)

    teams = session.exec(select(Team).where(Team.id.in_(team_ids))).all() if team_ids else []
    team_map = {tm.id: tm for tm in teams}

    trade_ids = [t.id for t in trades]
    all_trade_items = session.exec(select(TradeItem).where(TradeItem.trade_id.in_(trade_ids))).all() if trade_ids else []
    trade_items_map: dict[int, list[TradeItem]] = {}
    for it in all_trade_items:
        trade_items_map.setdefault(it.trade_id, []).append(it)

    trade_responses = []
    for trade in trades:
        # Get teams from map
        team1 = team_map.get(trade.team1_id)
        team2 = team_map.get(trade.team2_id)
        
        # Get trade items from map
        trade_items = trade_items_map.get(trade.id, [])
        
        # Organize trade items by team
        items_data = []
        for item in trade_items:
            team_name = team1.name if (team1 and item.team_id == team1.id) else (team2.name if team2 else "")
            items_data.append({
                "team_id": item.team_id,
                "player_name": item.player_name,
                "team_name": team_name
            })
        
        trade_responses.append(TradeDetailResponse(
            id=trade.id,
            league_id=trade.league_id,
            team1_id=trade.team1_id,
            team1_name=team1.name if team1 else "",
            team2_id=trade.team2_id,
            team2_name=team2.name if team2 else "",
            status=trade.status,
            proposed_at=trade.proposed_at,
            responded_at=trade.responded_at,
            trade_items=items_data
        ))
    
    return trade_responses

@router.put("/{trade_id}/accept")
def accept_trade(
    trade_id: int,
    _: None = Depends(enforce_team_unlocked),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Accept a pending trade."""
    # Roster lock enforced by dependency
    
    # Get trade
    trade = session.exec(select(Trade).where(Trade.id == trade_id)).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.status != TradeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Trade is not pending")
    
    # Verify current user owns the receiving team (team2)
    receiving_team = session.exec(select(Team).where(Team.id == trade.team2_id)).first()
    if receiving_team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only accept trades for your own team")
    
    # Get trade items
    trade_items = session.exec(
        select(TradeItem).where(TradeItem.trade_id == trade_id)
    ).all()
    
    # Execute the trade - swap players between teams
    for item in trade_items:
        # Find the player on their current team
        team_player = session.exec(
            select(TeamPlayer).where(
                TeamPlayer.team_id == item.team_id,
                TeamPlayer.player_name == item.player_name
            )
        ).first()
        
        if not team_player:
            # Rollback and raise error if player is missing
            session.rollback()
            raise HTTPException(
                status_code=400, 
                detail=f"Player {item.player_name} is no longer on the expected team. Trade cannot be completed."
            )
        
        # Determine the destination team
        if item.team_id == trade.team1_id:
            new_team_id = trade.team2_id
        else:
            new_team_id = trade.team1_id
        
        # Update the player's team
        team_player.team_id = new_team_id
        session.add(team_player)
    
    # Update trade status
    trade.status = TradeStatus.ACCEPTED
    trade.responded_at = datetime.utcnow()
    session.add(trade)
    
    session.commit()
    
    # Trade accepted - clients will poll for updates
    return {"message": "Trade accepted and players swapped successfully"}

@router.put("/{trade_id}/reject")
def reject_trade(
    trade_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Reject a pending trade."""
    # Get trade
    trade = session.exec(select(Trade).where(Trade.id == trade_id)).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.status != TradeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Trade is not pending")
    
    # Verify current user owns the receiving team (team2)
    receiving_team = session.exec(select(Team).where(Team.id == trade.team2_id)).first()
    if receiving_team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only reject trades for your own team")
    
    # Update trade status
    trade.status = TradeStatus.REJECTED
    trade.responded_at = datetime.utcnow()
    session.add(trade)
    session.commit()
    
    return {"message": "Trade rejected"}

@router.put("/{trade_id}/cancel")
def cancel_trade(
    trade_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a pending trade (only by the proposer)."""
    # Get trade
    trade = session.exec(select(Trade).where(Trade.id == trade_id)).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.status != TradeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Trade is not pending")
    
    # Verify current user owns the offering team (team1)
    offering_team = session.exec(select(Team).where(Team.id == trade.team1_id)).first()
    if offering_team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only cancel trades you proposed")
    
    # Update trade status
    trade.status = TradeStatus.CANCELLED
    trade.responded_at = datetime.utcnow()
    session.add(trade)
    session.commit()
    
    return {"message": "Trade cancelled"}

@router.get("/team/{team_id}", response_model=List[TradeDetailResponse])
def get_team_trades(
    team_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    """Get all trades involving a specific team."""
    # Verify team exists and user owns it
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view trades for your own team")
    
    # Get all trades involving this team
    trades = session.exec(
        select(Trade).where(
            (Trade.team1_id == team_id) | (Trade.team2_id == team_id)
        ).order_by(Trade.proposed_at.desc())
    ).all()
    
    # Fetch teams and trade items in bulk to avoid N+1 queries
    team_ids: set[int] = set()
    for t in trades:
        team_ids.add(t.team1_id)
        team_ids.add(t.team2_id)
    
    teams = session.exec(select(Team).where(Team.id.in_(team_ids))).all() if team_ids else []
    team_map = {tm.id: tm for tm in teams}
    
    trade_ids = [t.id for t in trades]
    all_trade_items = session.exec(select(TradeItem).where(TradeItem.trade_id.in_(trade_ids))).all() if trade_ids else []
    trade_items_map: dict[int, list[TradeItem]] = {}
    for it in all_trade_items:
        trade_items_map.setdefault(it.trade_id, []).append(it)
    
    trade_responses = []
    for trade in trades:
        # Get teams from map
        team1 = team_map.get(trade.team1_id)
        team2 = team_map.get(trade.team2_id)
        
        # Get trade items from map
        trade_items = trade_items_map.get(trade.id, [])
        
        # Organize trade items by team
        items_data = []
        for item in trade_items:
            team_name = team1.name if (team1 and item.team_id == team1.id) else (team2.name if team2 else "")
            items_data.append({
                "team_id": item.team_id,
                "player_name": item.player_name,
                "team_name": team_name
            })
        
        trade_responses.append(TradeDetailResponse(
            id=trade.id,
            league_id=trade.league_id,
            team1_id=trade.team1_id,
            team1_name=team1.name if team1 else "",
            team2_id=trade.team2_id,
            team2_name=team2.name if team2 else "",
            status=trade.status,
            proposed_at=trade.proposed_at,
            responded_at=trade.responded_at,
            trade_items=items_data
        ))
    
    return trade_responses
