"""
Admin panel router for managing players, users, leagues, and viewing analytics.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.database import get_session
from app.models.admin_model import Admin
from app.models.player_pool_model import Players
from app.models.user_model import User
from app.models.agent_model import Agent
from app.models.league_models import League, Team, LeagueMember, LeagueSettings
from app.models.match_model import Match
from app.models.live_data_models import PlayerStat
from app.utils.admin_auth import (
    get_current_active_admin,
    require_player_management,
    require_user_management,
    require_league_management,
    require_analytics_access
)

router = APIRouter(prefix="/admin", tags=["admin"])

# Pydantic models for responses
class PlayerResponse(BaseModel):
    player_name: str
    team: str
    primary_role: Optional[str]
    image_url: Optional[str]
    total_matches: int
    total_points: float
    average_points: float
    total_kills: int
    total_assists: int
    total_deaths: int

class PlayerUpdate(BaseModel):
    team: Optional[str] = None
    primary_role: Optional[str] = None
    image_url: Optional[str] = None

class PlayerCreate(BaseModel):
    player_name: str
    team: str
    primary_role: Optional[str] = None
    image_url: Optional[str] = None

class AgentResponse(BaseModel):
    id: int
    name: str
    agent_class: str
    is_active: bool
    release_date: Optional[str]
    image_url: Optional[str]
    description: Optional[str]
    created_at: str
    updated_at: str

class AgentCreate(BaseModel):
    name: str
    agent_class: str
    release_date: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

class AgentUpdate(BaseModel):
    agent_class: Optional[str] = None
    is_active: Optional[bool] = None
    release_date: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None

class UserAnalytics(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str
    leagues_count: int
    teams_count: int

class LeagueAnalytics(BaseModel):
    id: int
    name: str
    description: Optional[str]
    max_teams: int
    current_teams: int
    status: str
    created_at: str
    members_count: int

class SystemAnalytics(BaseModel):
    total_users: int
    active_users_last_30_days: int
    total_leagues: int
    active_leagues: int
    total_players: int
    total_matches: int
    recent_registrations: List[Dict[str, Any]]

# Player Management Endpoints
@router.get("/players", response_model=List[PlayerResponse])
async def get_all_players(
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_analytics_access),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    team_filter: Optional[str] = Query(None),
    role_filter: Optional[str] = Query(None)
):
    """Get all players with their statistics and performance data."""
    
    query = select(Players)
    
    if team_filter:
        query = query.where(Players.team == team_filter)
    if role_filter:
        query = query.where(Players.primary_role == role_filter)
    
    query = query.offset(offset).limit(limit)
    players = session.exec(query).all()
    
    player_responses = []
    for player in players:
        # Calculate player statistics
        stats_query = select(
            func.count(PlayerStat.match_id.distinct()).label('total_matches'),
            func.sum(PlayerStat.score).label('total_points'),
            func.sum(PlayerStat.kills).label('total_kills'),
            func.sum(PlayerStat.assists).label('total_assists'),
            func.sum(PlayerStat.deaths).label('total_deaths')
        ).where(PlayerStat.player_name == player.player_name)
        
        stats = session.exec(stats_query).first()
        
        total_matches = int(stats.total_matches or 0)
        total_points = float(stats.total_points or 0)
        average_points = total_points / total_matches if total_matches > 0 else 0
        
        player_responses.append(PlayerResponse(
            player_name=player.player_name,
            team=player.team,
            primary_role=player.primary_role,
            image_url=player.image_url,
            total_matches=total_matches,
            total_points=total_points,
            average_points=round(average_points, 2),
            total_kills=int(stats.total_kills or 0),
            total_assists=int(stats.total_assists or 0),
            total_deaths=int(stats.total_deaths or 0)
        ))
    
    return player_responses

@router.post("/players", response_model=PlayerResponse, status_code=status.HTTP_201_CREATED)
async def create_player(
    player_data: PlayerCreate,
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_player_management)
):
    """Create a new player."""
    
    # Check if player already exists
    existing_player = session.exec(select(Players).where(Players.player_name == player_data.player_name)).first()
    if existing_player:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Player with this name already exists"
        )
    
    new_player = Players(
        player_name=player_data.player_name,
        team=player_data.team,
        primary_role=player_data.primary_role,
        image_url=player_data.image_url
    )
    
    session.add(new_player)
    session.commit()
    session.refresh(new_player)
    
    return PlayerResponse(
        player_name=new_player.player_name,
        team=new_player.team,
        primary_role=new_player.primary_role,
        image_url=new_player.image_url,
        total_matches=0,
        total_points=0.0,
        average_points=0.0,
        total_kills=0,
        total_assists=0,
        total_deaths=0
    )

@router.put("/players/{player_name}", response_model=PlayerResponse)
async def update_player(
    player_name: str,
    player_data: PlayerUpdate,
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_player_management)
):
    """Update player information."""
    
    player = session.exec(select(Players).where(Players.player_name == player_name)).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    # Update fields if provided
    if player_data.team is not None:
        player.team = player_data.team
    if player_data.primary_role is not None:
        player.primary_role = player_data.primary_role
    if player_data.image_url is not None:
        player.image_url = player_data.image_url
    
    session.add(player)
    session.commit()
    session.refresh(player)
    
    # Get updated statistics
    stats_query = select(
        func.count(PlayerStat.match_id.distinct()).label('total_matches'),
        func.sum(PlayerStat.score).label('total_points'),
        func.sum(PlayerStat.kills).label('total_kills'),
        func.sum(PlayerStat.assists).label('total_assists'),
        func.sum(PlayerStat.deaths).label('total_deaths')
    ).where(PlayerStat.player_name == player.player_name)
    
    stats = session.exec(stats_query).first()
    
    total_matches = int(stats.total_matches or 0)
    total_points = float(stats.total_points or 0)
    average_points = total_points / total_matches if total_matches > 0 else 0
    
    return PlayerResponse(
        player_name=player.player_name,
        team=player.team,
        primary_role=player.primary_role,
        image_url=player.image_url,
        total_matches=total_matches,
        total_points=total_points,
        average_points=round(average_points, 2),
        total_kills=int(stats.total_kills or 0),
        total_assists=int(stats.total_assists or 0),
        total_deaths=int(stats.total_deaths or 0)
    )

@router.delete("/players/{player_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_player(
    player_name: str,
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_player_management)
):
    """Delete a player from the system."""
    
    player = session.exec(select(Players).where(Players.player_name == player_name)).first()
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    session.delete(player)
    session.commit()

# User Management Endpoints
@router.get("/users", response_model=List[UserAnalytics])
async def get_all_users(
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_user_management),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all users with their league and team information."""
    
    users = session.exec(select(User).offset(offset).limit(limit)).all()
    
    user_analytics = []
    for user in users:
        leagues_count = len(user.league_memberships)
        teams_count = len(user.teams)
        
        user_analytics.append(UserAnalytics(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            leagues_count=leagues_count,
            teams_count=teams_count
        ))
    
    return user_analytics

# League Management Endpoints
@router.get("/leagues", response_model=List[LeagueAnalytics])
async def get_all_leagues(
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_league_management),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get all leagues with their member and team information."""
    
    leagues = session.exec(select(League).offset(offset).limit(limit)).all()
    
    league_analytics = []
    for league in leagues:
        current_teams = len(league.teams)
        members_count = len(league.members)
        
        league_analytics.append(LeagueAnalytics(
            id=league.id,
            name=league.name,
            description=league.description,
            max_teams=league.max_teams,
            current_teams=current_teams,
            status=league.status.value,
            created_at=league.created_at.isoformat(),
            members_count=members_count
        ))
    
    return league_analytics

# System Analytics Endpoints
@router.get("/analytics/system", response_model=SystemAnalytics)
async def get_system_analytics(
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_analytics_access)
):
    """Get comprehensive system analytics and statistics."""
    
    # Count totals
    total_users = session.exec(select(func.count(User.id))).first()
    total_leagues = session.exec(select(func.count(League.id))).first()
    total_players = session.exec(select(func.count(Players.player_name))).first()
    total_matches = session.exec(select(func.count(Match.id))).first()
    
    # Active users in last 30 days (users who have teams or league memberships)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users = session.exec(
        select(func.count(User.id.distinct()))
        .join(LeagueMember, User.id == LeagueMember.user_id)
        .where(LeagueMember.joined_at >= thirty_days_ago)
    ).first()
    
    # Active leagues (not completed)
    active_leagues = session.exec(
        select(func.count(League.id))
        .where(League.status != "COMPLETED")
    ).first()
    
    # Recent registrations (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_users = session.exec(
        select(User.username, User.created_at)
        .where(User.created_at >= seven_days_ago)
        .order_by(User.created_at.desc())
        .limit(10)
    ).all()
    
    recent_registrations = [
        {
            "username": user.username,
            "created_at": user.created_at.isoformat()
        }
        for user in recent_users
    ]
    
    return SystemAnalytics(
        total_users=int(total_users),
        active_users_last_30_days=int(active_users or 0),
        total_leagues=int(total_leagues),
        active_leagues=int(active_leagues),
        total_players=int(total_players),
        total_matches=int(total_matches),
        recent_registrations=recent_registrations
    )

@router.get("/analytics/players/top", response_model=List[PlayerResponse])
async def get_top_players(
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_analytics_access),
    limit: int = Query(10, le=50),
    sort_by: str = Query("total_points", regex="^(total_points|average_points|total_kills)$")
):
    """Get top performing players based on different metrics."""
    
    # Get all players with their statistics
    players_with_stats = []
    players = session.exec(select(Players)).all()
    
    for player in players:
        stats_query = select(
            func.count(PlayerStat.match_id.distinct()).label('total_matches'),
            func.sum(PlayerStat.score).label('total_points'),
            func.sum(PlayerStat.kills).label('total_kills'),
            func.sum(PlayerStat.assists).label('total_assists'),
            func.sum(PlayerStat.deaths).label('total_deaths')
        ).where(PlayerStat.player_name == player.player_name)
        
        stats = session.exec(stats_query).first()
        
        total_matches = int(stats.total_matches or 0)
        total_points = float(stats.total_points or 0)
        average_points = total_points / total_matches if total_matches > 0 else 0
        
        player_response = PlayerResponse(
            player_name=player.player_name,
            team=player.team,
            primary_role=player.primary_role,
            image_url=player.image_url,
            total_matches=total_matches,
            total_points=total_points,
            average_points=round(average_points, 2),
            total_kills=int(stats.total_kills or 0),
            total_assists=int(stats.total_assists or 0),
            total_deaths=int(stats.total_deaths or 0)
        )
        
        players_with_stats.append(player_response)
    
    # Sort based on the requested metric
    if sort_by == "total_points":
        players_with_stats.sort(key=lambda x: x.total_points, reverse=True)
    elif sort_by == "average_points":
        players_with_stats.sort(key=lambda x: x.average_points, reverse=True)
    elif sort_by == "total_kills":
                                players_with_stats.sort(key=lambda x: x.total_kills, reverse=True)
    
    return players_with_stats[:limit]

# Agent Management Endpoints
@router.get("/agents", response_model=List[AgentResponse])
async def get_all_agents(
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_player_management),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    class_filter: Optional[str] = Query(None),
    active_only: bool = Query(True)
):
    """Get all agents with filtering options."""
    
    query = select(Agent)
    
    if active_only:
        query = query.where(Agent.is_active == True)
    if class_filter:
        query = query.where(Agent.agent_class == class_filter)
    
    query = query.offset(offset).limit(limit).order_by(Agent.agent_class, Agent.name)
    agents = session.exec(query).all()
    
    return [
        AgentResponse(
            id=agent.id,
            name=agent.name,
            agent_class=agent.agent_class,
            is_active=agent.is_active,
            release_date=agent.release_date,
            image_url=agent.image_url,
            description=agent.description,
            created_at=agent.created_at.isoformat(),
            updated_at=agent.updated_at.isoformat()
        )
        for agent in agents
    ]

@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_player_management)
):
    """Create a new agent."""
    
    # Validate agent class
    from app.utils.agents import VALID_CLASSES
    if agent_data.agent_class not in VALID_CLASSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent class. Must be one of: {', '.join(VALID_CLASSES)}"
        )
    
    # Check if agent already exists
    existing_agent = session.exec(select(Agent).where(Agent.name == agent_data.name)).first()
    if existing_agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent with this name already exists"
        )
    
    new_agent = Agent(
        name=agent_data.name,
        agent_class=agent_data.agent_class,
        release_date=agent_data.release_date,
        image_url=agent_data.image_url,
        description=agent_data.description
    )
    
    session.add(new_agent)
    session.commit()
    session.refresh(new_agent)
    
    return AgentResponse(
        id=new_agent.id,
        name=new_agent.name,
        agent_class=new_agent.agent_class,
        is_active=new_agent.is_active,
        release_date=new_agent.release_date,
        image_url=new_agent.image_url,
        description=new_agent.description,
        created_at=new_agent.created_at.isoformat(),
        updated_at=new_agent.updated_at.isoformat()
    )

@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_player_management)
):
    """Update agent information."""
    
    agent = session.exec(select(Agent).where(Agent.id == agent_id)).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Validate agent class if provided
    if agent_data.agent_class is not None:
        from app.utils.agents import VALID_CLASSES
        if agent_data.agent_class not in VALID_CLASSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent class. Must be one of: {', '.join(VALID_CLASSES)}"
            )
        agent.agent_class = agent_data.agent_class
    
    # Update fields if provided
    if agent_data.is_active is not None:
        agent.is_active = agent_data.is_active
    if agent_data.release_date is not None:
        agent.release_date = agent_data.release_date
    if agent_data.image_url is not None:
        agent.image_url = agent_data.image_url
    if agent_data.description is not None:
        agent.description = agent_data.description
    
    agent.updated_at = datetime.utcnow()
    
    session.add(agent)
    session.commit()
    session.refresh(agent)
    
    return AgentResponse(
        id=agent.id,
        name=agent.name,
        agent_class=agent.agent_class,
        is_active=agent.is_active,
        release_date=agent.release_date,
        image_url=agent.image_url,
        description=agent.description,
        created_at=agent.created_at.isoformat(),
        updated_at=agent.updated_at.isoformat()
    )

@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_player_management)
):
    """Delete an agent from the system."""
    
    agent = session.exec(select(Agent).where(Agent.id == agent_id)).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    session.delete(agent)
    session.commit()

@router.post("/agents/import-defaults", status_code=status.HTTP_201_CREATED)
async def import_default_agents(
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_player_management)
):
    """Import default Valorant agents into the database."""
    
    from app.utils.agents import FALLBACK_AGENT_TO_CLASS
    
    imported_count = 0
    existing_agents = {agent.name for agent in session.exec(select(Agent)).all()}
    
    for agent_name, agent_class in FALLBACK_AGENT_TO_CLASS.items():
        if agent_name not in existing_agents:
            new_agent = Agent(
                name=agent_name,
                agent_class=agent_class,
                description=f"Default {agent_class} agent"
            )
            session.add(new_agent)
            imported_count += 1
    
    session.commit()
    
    return {
        "message": f"Successfully imported {imported_count} default agents",
        "imported_count": imported_count
    }

@router.get("/analytics/teams")
async def get_team_analytics(
    session: Session = Depends(get_session),
    admin: Admin = Depends(require_analytics_access)
):
    """Get analytics about teams and their distribution."""
    
    # Get team distribution
    team_stats = session.exec(
        select(Players.team, func.count(Players.player_name).label('player_count'))
        .group_by(Players.team)
        .order_by(func.count(Players.player_name).desc())
    ).all()
    
    return {
        "team_distribution": [
            {"team": team, "player_count": int(count)}
            for team, count in team_stats
        ]
    }
