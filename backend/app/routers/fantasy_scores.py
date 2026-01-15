"""
Fantasy scoring API endpoints for retrieving team and player performance data.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from app.database import get_session
from app.models.league_models import (
    League, Team, TeamPlayer, DraftPick, LeagueMember, LeagueSettings
)
from app.models.player_pool_model import Players
from app.models.user_model import User
from app.models.match_model import Match
from app.models.live_data_models import LiveScore, PlayerStat
from app.models.league_models import AgentPrediction
from app.utils.agents import get_agent_to_class_mapping

# Helper functions for event-based scoring and best 2 of 3 scoring
def calculate_best_2_of_3_score(player_name: str, match_id: int, session: Session) -> float:
    """
    Calculate the best 2 of 3 map scores for a player in a specific match.
    If player played 3 maps, only the best 2 are counted.
    If player played 1-2 maps, all maps are counted.
    """
    # Get all map scores for this player in this match
    map_scores = session.exec(
        select(PlayerStat.score, PlayerStat.map_name)
        .where(
            and_(
                PlayerStat.player_name == player_name,
                PlayerStat.match_id == match_id,
                PlayerStat.score.is_not(None)
            )
        )
        .order_by(PlayerStat.score.desc())  # Order by score descending
    ).all()
    
    if not map_scores:
        return 0.0
    
    # Extract just the scores
    scores = [float(score) for score, _ in map_scores if score is not None]
    
    # If 1-2 maps, use all scores
    if len(scores) <= 2:
        return sum(scores)
    
    # If 3+ maps, use only the best 2
    return sum(scores[:2])

# def _apply_agent_prediction_multiplier(
#     session: Session,
#     team_id: int,
#     player_name: str,
#     match_id: int,
#     base_score: float
# ) -> float:
#     """
#     Apply prediction multipliers based on user's agent picks.
#     - If actual agent in top 3 picks => 1.0x (full points)
#     - Else if actual agent class matches class of any picked agent => 0.5x
#     - Else => 0.25x
#     If no prediction exists, return base_score (1.0x) to avoid penalizing.
#     """
#     pred = session.exec(
#         select(AgentPrediction).where(
#             AgentPrediction.team_id == team_id,
#             AgentPrediction.player_name == player_name
#         )
#     ).first()
#     if not pred:
#         return base_score

#     # Get the actual agent used across maps in this match (use most frequent non-null)
#     stats = session.exec(
#         select(PlayerStat.agent)
#         .where(
#             and_(
#                 PlayerStat.player_name == player_name,
#                 PlayerStat.match_id == match_id,
#                 PlayerStat.agent.is_not(None)
#             )
#         )
#     ).all()
#     if not stats:
#         return base_score
#     agents_used = [a for (a,) in stats if a]

#     picks = [p.strip() for p in pred.picks_csv.split(',') if p.strip()]
#     agent_to_class = get_agent_to_class_mapping(session)
#     pick_classes = {agent_to_class.get(p) for p in picks if agent_to_class.get(p)}

#     # Load league settings to get multipliers
#     team = session.exec(select(Team).where(Team.id == team_id)).first()
#     if not team:
#         return base_score
#     league_settings = session.exec(select(LeagueSettings).where(LeagueSettings.league_id == team.league_id)).first()
#     exact_mult = league_settings.agent_exact_match_multiplier if league_settings else 1.0
#     class_mult = league_settings.agent_class_match_multiplier if league_settings else 0.5
#     miss_mult = league_settings.agent_miss_multiplier if league_settings else 0.25

#     exact_matches = sum(1 for a in agents_used if a in picks)
#     if exact_matches >= 2:
#         return base_score * float(exact_mult)

#     class_matches = sum(1 for a in agents_used if agent_to_class.get(a) in pick_classes)
#     if class_matches >= 1:
#         return base_score * float(class_mult)

#     return base_score * float(miss_mult)

def _calculate_match_score_with_agent_predictions(
    session: Session,
    team_id: int,
    player_name: str,
    match_id: int,
    use_best_2_of_3: bool = True,
) -> float:
    """
    Calculate the per-match score with agent prediction multipliers applied per-map,
    then choose the best combination (top 2 weighted maps if BO3; both if BO2).

    If no prediction exists for this player/team, falls back to base scoring.
    """
    # Fetch per-map scores and agents for this match
    map_stats = session.exec(
        select(PlayerStat.score, PlayerStat.agent)
        .where(
            and_(
                PlayerStat.player_name == player_name,
                PlayerStat.match_id == match_id,
                PlayerStat.score.is_not(None)
            )
        )
    ).all()
    if not map_stats:
        return 0.0

    # If no prediction exists, just return base best-2-of-3 scoring
    pred = session.exec(
        select(AgentPrediction).where(
            AgentPrediction.team_id == team_id,
            AgentPrediction.player_name == player_name
        )
    ).first()
    if not pred:
        base_scores = [float(s or 0.0) for s, _ in map_stats]
        base_scores.sort(reverse=True)
        if use_best_2_of_3:
            return sum(base_scores[:min(2, len(base_scores))])
        return sum(base_scores)

    # Normalize picks to uppercase
    picks = [p.strip().upper() for p in pred.picks_csv.split(',') if p.strip()]

    # Mapping agent -> class (normalize keys to uppercase for comparison)
    agent_to_class = get_agent_to_class_mapping(session)
    upper_agent_to_class = {str(k).upper(): v for k, v in agent_to_class.items()}
    pick_classes = {upper_agent_to_class.get(p) for p in picks if upper_agent_to_class.get(p)}

    # Load multipliers
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    league_settings = session.exec(select(LeagueSettings).where(LeagueSettings.league_id == team.league_id)).first() if team else None
    exact_mult = float(league_settings.agent_exact_match_multiplier) if league_settings else 1.0
    class_mult = float(league_settings.agent_class_match_multiplier) if league_settings else 0.5
    miss_mult = float(league_settings.agent_miss_multiplier) if league_settings else 0.25

    # Compute per-map weighted scores
    weighted_scores: list[float] = []
    for sc, agent in map_stats:
        base = float(sc or 0.0)
        if not agent:
            mult = miss_mult
        else:
            agent_upper = str(agent).upper()
            if agent_upper in picks:
                mult = exact_mult
            else:
                agent_class = upper_agent_to_class.get(agent_upper)
                if agent_class and agent_class in pick_classes:
                    mult = class_mult
                else:
                    mult = miss_mult
        weighted_scores.append(base * mult)

    # Select best combination according to scoring mode
    weighted_scores.sort(reverse=True)
    if use_best_2_of_3:
        return sum(weighted_scores[:min(2, len(weighted_scores))])
    return sum(weighted_scores)

def get_player_map_breakdown(player_name: str, match_id: int, session: Session) -> Dict[str, Any]:
    """
    Get detailed map breakdown for a player including which maps were counted.
    Returns a dictionary with map details and best 2 of 3 calculation info.
    """
    map_stats = session.exec(
        select(PlayerStat)
        .where(
            and_(
                PlayerStat.player_name == player_name,
                PlayerStat.match_id == match_id
            )
        )
        .order_by(PlayerStat.score.desc())
    ).all()
    
    if not map_stats:
        return {
            "maps_played": 0,
            "total_maps": 0,
            "best_2_score": 0.0,
            "all_maps_score": 0.0,
            "maps": [],
            "counted_maps": []
        }
    
    maps_data = []
    total_score = 0.0
    
    for stat in map_stats:
        map_data = {
            "map_name": stat.map_name,
            "score": float(stat.score or 0),
            "kills": stat.kills,
            "deaths": stat.deaths,
            "assists": stat.assists,
            "agent": stat.agent
        }
        maps_data.append(map_data)
        total_score += float(stat.score or 0)
    
    # Sort by score descending for best 2 calculation
    maps_data.sort(key=lambda x: x["score"], reverse=True)
    
    # Determine which maps count for best 2 of 3
    maps_counted = min(2, len(maps_data))
    counted_maps = maps_data[:maps_counted]
    best_2_score = sum(map_data["score"] for map_data in counted_maps)
    
    return {
        "maps_played": len(maps_data),
        "total_maps": len(maps_data),
        "best_2_score": best_2_score,
        "all_maps_score": total_score,
        "maps": maps_data,
        "counted_maps": counted_maps
    }

def get_available_events(session) -> List[str]:
    """
    Returns all available VCT events from the database.
    """
    events = session.exec(
        select(Match.match_event)
        .where(
            or_(
                Match.match_event.like("VCT %"),
                Match.match_event.like("Masters %"),
                Match.match_event.like("Champions %"),
                Match.match_event.like("Valorant Masters %")
            )
        )
        .distinct()
        .order_by(Match.match_event)
    ).all()
    return events

def calculate_player_score_with_best_2_of_3(player_name: str, event: str, session: Session, use_best_2_of_3: bool = True) -> Dict[str, Any]:
    """
    Calculate a player's total score for an event, optionally using best 2 of 3 scoring.
    Returns detailed breakdown including match-by-match scores.
    """
    # Get all matches for this player in the specified event
    matches = session.exec(
        select(Match.id, Match.match_event, Match.team1, Match.team2)
        .join(PlayerStat, PlayerStat.match_id == Match.id)
        .where(
            and_(
                PlayerStat.player_name == player_name,
                Match.match_event == event
            )
        )
        .distinct()
    ).all()
    
    total_score = 0.0
    total_kills = 0
    total_deaths = 0
    total_assists = 0
    matches_played = 0
    match_breakdowns = []
    
    for match in matches:
        match_id = match.id
        
        if use_best_2_of_3:
            # Use best 2 of 3 scoring
            match_score = calculate_best_2_of_3_score(player_name, match_id, session)
            map_breakdown = get_player_map_breakdown(player_name, match_id, session)
        else:
            # Use all maps scoring (traditional)
            match_stats = session.exec(
                select(
                    func.sum(PlayerStat.score).label('total_score'),
                    func.sum(PlayerStat.kills).label('total_kills'),
                    func.sum(PlayerStat.assists).label('total_assists'),
                    func.sum(PlayerStat.deaths).label('total_deaths')
                )
                .where(
                    and_(
                        PlayerStat.player_name == player_name,
                        PlayerStat.match_id == match_id
                    )
                )
            ).first()
            
            match_score = float(match_stats.total_score or 0)
            map_breakdown = get_player_map_breakdown(player_name, match_id, session)
        
        if match_score > 0:
            # Get match stats for kills/deaths/assists regardless of scoring method
            match_stats = session.exec(
                select(
                    func.sum(PlayerStat.kills).label('total_kills'),
                    func.sum(PlayerStat.assists).label('total_assists'),
                    func.sum(PlayerStat.deaths).label('total_deaths')
                )
                .where(
                    and_(
                        PlayerStat.player_name == player_name,
                        PlayerStat.match_id == match_id
                    )
                )
            ).first()
            
            match_kills = int(match_stats.total_kills or 0)
            match_deaths = int(match_stats.total_deaths or 0)
            match_assists = int(match_stats.total_assists or 0)
            
            total_score += match_score
            total_kills += match_kills
            total_deaths += match_deaths
            total_assists += match_assists
            matches_played += 1
            
            match_breakdowns.append({
                "match_id": match_id,
                "team1": match.team1,
                "team2": match.team2,
                "score": match_score,
                "kills": match_kills,
                "deaths": match_deaths,
                "assists": match_assists,
                "maps_breakdown": map_breakdown,
                "scoring_method": "best_2_of_3" if use_best_2_of_3 else "all_maps"
            })
    
    return {
        "player_name": player_name,
        "total_score": total_score,
        "total_kills": total_kills,
        "total_deaths": total_deaths,
        "total_assists": total_assists,
        "matches_played": matches_played,
        "average_score": total_score / matches_played if matches_played > 0 else 0,
        "match_breakdowns": match_breakdowns,
        "scoring_method": "best_2_of_3" if use_best_2_of_3 else "all_maps"
    }

def get_current_event(session) -> str:
    """
    Returns the current VCT event based on live matches.
    Prioritizes EMEA and Americas as the primary live regions.
    """
    import time
    current_time = int(time.time())
    four_hours_ago = current_time - (4 * 60 * 60)  # 4 hours in seconds

    # Check for live matches in priority order: EMEA, Americas
    priority_regions = ["EMEA", "Americas"]

    for region in priority_regions:
        # Check if this region has recent matches (within 4 hours)
        recent_event = session.exec(
            select(Match.match_event)
            .where(
                and_(
                    Match.match_event.like(f"VCT 2025: {region}%"),
                    Match.unix_timestamp >= four_hours_ago,
                    Match.unix_timestamp <= current_time  # Only past/current matches
                )
            )
            .order_by(Match.unix_timestamp.desc())
            .limit(1)
        ).first()

        if recent_event:
            return recent_event

    # Fallback: check for any VCT 2025 Stage 2 event with recent activity
    fallback_event = session.exec(
        select(Match.match_event)
        .where(
            and_(
                Match.match_event.like("VCT 2025:%Stage 2"),
                Match.unix_timestamp >= four_hours_ago,
                Match.unix_timestamp <= current_time
            )
        )
        .order_by(Match.unix_timestamp.desc())
        .limit(1)
    ).first()

    if fallback_event:
        return fallback_event

    # Final fallback: return EMEA as default
    return "VCT 2025: EMEA Stage 2"

router = APIRouter(prefix="/fantasy", tags=["Fantasy Scores"])

# Response Models for events
class EventResponse(BaseModel):
    event_name: str
    match_count: int
    is_current: bool

class EventsListResponse(BaseModel):
    events: List[EventResponse]
    current_event: str

# Response Models
class PlayerScoreResponse(BaseModel):
    player_name: str
    total_score: float
    total_kills: int
    total_assists: int
    total_deaths: int
    matches_played: int
    average_score: float

class TeamScoreResponse(BaseModel):
    team_id: int
    team_name: str
    user_id: int
    username: Optional[str] = None
    total_score: float
    player_count: int
    average_player_score: float
    top_player: Optional[str] = None
    top_player_score: Optional[float] = None

class LeagueLeaderboardResponse(BaseModel):
    league_id: int
    league_name: str
    teams: List[TeamScoreResponse]
    last_updated: datetime

class TeamDetailResponse(BaseModel):
    team_id: int
    team_name: str
    user_id: int
    total_score: float  # Only from starting players
    starting_players: List[PlayerScoreResponse]
    bench_players: List[PlayerScoreResponse]
    recent_matches: List[Dict[str, Any]]

class LiveMatchResponse(BaseModel):
    match_id: int
    team1: str
    team2: str
    current_map: str
    team1_score: str
    team2_score: str
    live_player_scores: List[Dict[str, Any]]

class MatchStatusResponse(BaseModel):
    match_id: int
    team1: str
    team2: str
    match_event: str
    scheduled_time: int
    status: str  # "upcoming", "live", "completed"
    time_until_match: Optional[int] = None  # seconds until match (negative if started)
    match_page: str
    last_scraped: Optional[datetime] = None
    has_live_data: bool = False

# Response models for detailed scoring with best 2 of 3
class MapScoreResponse(BaseModel):
    map_name: str
    score: float
    kills: int
    deaths: int
    assists: int
    agent: Optional[str]

class MatchBreakdownResponse(BaseModel):
    match_id: int
    team1: str
    team2: str
    score: float
    kills: int
    deaths: int
    assists: int
    maps_breakdown: Dict[str, Any]
    scoring_method: str

class DetailedPlayerScoreResponse(BaseModel):
    player_name: str
    total_score: float
    total_kills: int
    total_deaths: int
    total_assists: int
    matches_played: int
    average_score: float
    match_breakdowns: List[MatchBreakdownResponse]
    scoring_method: str


def _dedupe_team_scores_by_user(team_responses: List[TeamScoreResponse]) -> List[TeamScoreResponse]:
    """Ensure only one team per user appears on the leaderboard.
    Picks the entry with more starting players first, then higher total score.
    """
    best_by_user: dict[int, TeamScoreResponse] = {}
    for tr in team_responses:
        existing = best_by_user.get(tr.user_id)
        if existing is None:
            best_by_user[tr.user_id] = tr
            continue
        if (tr.player_count, tr.total_score) > (existing.player_count, existing.total_score):
            best_by_user[tr.user_id] = tr
    return list(best_by_user.values())

@router.get("/events", response_model=EventsListResponse)
async def get_available_events(
    session: Session = Depends(get_session)
):
    """Get all available VCT events for fantasy scoring."""

    # Get all events with match counts
    events_data = session.exec(
        select(Match.match_event, func.count(Match.id).label('match_count'))
        .where(
            or_(
                Match.match_event.like("VCT %"),
                Match.match_event.like("Masters %"),
                Match.match_event.like("Champions %"),
                Match.match_event.like("Valorant Masters %")
            )
        )
        .group_by(Match.match_event)
        .order_by(Match.match_event)
    ).all()

    current_event = get_current_event(session)

    events = [
        EventResponse(
            event_name=event_name,
            match_count=match_count,
            is_current=(event_name == current_event)
        )
        for event_name, match_count in events_data
    ]

    return EventsListResponse(
        events=events,
        current_event=current_event
    )


@router.get("/leagues/{league_id}/leaderboard", response_model=LeagueLeaderboardResponse)
async def get_league_leaderboard(
    league_id: int,
    event: Optional[str] = Query(None, description="Specific event to filter scores (e.g., 'VCT 2025: Stage 2'). If not provided, uses current event."),
    session: Session = Depends(get_session)
):
    """Get the current leaderboard for a league with team scores."""

    # Verify league exists
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    # Determine which event to use
    if event is None:
        event = get_current_event(session)

    # Get all teams in the league
    teams = session.exec(
        select(Team).where(Team.league_id == league_id)
    ).all()

    # Get league settings to check if best 2 of 3 scoring is enabled
    league_settings = session.exec(
        select(LeagueSettings).where(LeagueSettings.league_id == league_id)
    ).first()
    
    use_best_2_of_3 = league_settings.use_best_2_of_3 if league_settings else True

    team_responses = []
    # Preload users map to avoid repeated queries
    user_ids = [t.user_id for t in teams]
    user_id_to_name = {}
    if user_ids:
        users = session.exec(select(User).where(User.id.in_(user_ids))).all()
        user_id_to_name = {u.id: u.username for u in users}
    for team in teams:
        # Get ONLY STARTING players on this team
        team_players = session.exec(
            select(TeamPlayer, Players)
            .join(Players, TeamPlayer.player_name == Players.player_name)
            .where(
                and_(
                    TeamPlayer.team_id == team.id,
                    TeamPlayer.is_starting == True  # ONLY starting players
                )
            )
        ).all()

        total_team_score = 0
        starting_player_count = len(team_players)
        top_player_name = None
        top_player_score = 0

        for team_player, player in team_players:
            # Calculate player score using best 2 of 3 or traditional method
            player_data = calculate_player_score_with_best_2_of_3(
                player.player_name, 
                event, 
                session, 
                use_best_2_of_3
            )
            # Apply prediction multiplier per match component
            total = 0.0
            for m in player_data["match_breakdowns"]:
                total += _calculate_match_score_with_agent_predictions(
                    session,
                    team.id,
                    player.player_name,
                    m["match_id"],
                    use_best_2_of_3,
                )
            score = total
            
            total_team_score += score

            if score > top_player_score:
                top_player_score = score
                top_player_name = player.player_name

        average_score = total_team_score / starting_player_count if starting_player_count > 0 else 0

        team_response = TeamScoreResponse(
            team_id=team.id,
            team_name=team.name,
            user_id=team.user_id,
            username=user_id_to_name.get(team.user_id),
            total_score=total_team_score,
            player_count=starting_player_count,  # Only starting players count
            average_player_score=average_score,
            top_player=top_player_name,
            top_player_score=top_player_score if top_player_score > 0 else None
        )
        team_responses.append(team_response)

    # Dedupe teams per user and sort desc by score
    team_responses = _dedupe_team_scores_by_user(team_responses)
    team_responses.sort(key=lambda x: x.total_score, reverse=True)
    
    return LeagueLeaderboardResponse(
        league_id=league_id,
        league_name=league.name,
        teams=team_responses,
        last_updated=datetime.now(timezone.utc)
    )


def _calculate_player_score_in_time_range(
    session: Session,
    player_name: str,
    start_ts: int,
    end_ts: int,
    use_best_2_of_3: bool
) -> float:
    """
    Calculate a player's total score across matches in a time range.
    Applies best 2 of 3 per match if enabled.
    """
    matches = session.exec(
        select(Match.id)
        .join(PlayerStat, PlayerStat.match_id == Match.id)
        .where(
            and_(
                PlayerStat.player_name == player_name,
                Match.unix_timestamp >= start_ts,
                Match.unix_timestamp <= end_ts,
                or_(
                    Match.match_event.like("VCT %"),
                    Match.match_event.like("Masters %"),
                    Match.match_event.like("Champions %"),
                    Match.match_event.like("Valorant Masters %")
                )
            )
        )
        .distinct()
    ).all()

    total = 0.0
    for match_id in matches:
        if use_best_2_of_3:
            total += calculate_best_2_of_3_score(player_name, match_id, session)
        else:
            stats = session.exec(
                select(func.sum(PlayerStat.score).label('total_score'))
                .where(
                    and_(
                        PlayerStat.player_name == player_name,
                        PlayerStat.match_id == match_id
                    )
                )
            ).first()
            total += float(stats.total_score or 0)

    return total


@router.get("/leagues/{league_id}/leaderboard/weekly", response_model=LeagueLeaderboardResponse)
async def get_league_leaderboard_weekly(
    league_id: int,
    days: int = Query(7, ge=1, le=31, description="Number of days to include (default 7)"),
    session: Session = Depends(get_session)
):
    """
@router.get("/leagues/{league_id}/leaderboard/weekly", response_model=LeagueLeaderboardResponse)
async def get_league_leaderboard_weekly(
    league_id: int,
    days: int = Query(7, ge=1, le=31, description="Number of days to include (default 7)"),
    session: Session = Depends(get_session)
):
    Get weekly leaderboard for a league by summing starting player scores across all relevant matches.
    """
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    end_ts = int(datetime.now(timezone.utc).timestamp())
    start_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())

    teams = session.exec(select(Team).where(Team.league_id == league_id)).all()
    league_settings = session.exec(select(LeagueSettings).where(LeagueSettings.league_id == league_id)).first()
    use_best_2_of_3 = league_settings.use_best_2_of_3 if league_settings else True

    user_id_to_name = {}
    user_ids = [t.user_id for t in teams]
    if user_ids:
        users = session.exec(select(User).where(User.id.in_(user_ids))).all()
        user_id_to_name = {u.id: u.username for u in users}

    team_responses: list[TeamScoreResponse] = []
    for team in teams:
        team_players = session.exec(
            select(TeamPlayer, Players)
            .join(Players, TeamPlayer.player_name == Players.player_name)
            .where(and_(TeamPlayer.team_id == team.id, TeamPlayer.is_starting == True))
        ).all()

        total_team_score = 0.0
        starting_player_count = len(team_players)
        top_player_name = None
        top_player_score = 0.0

        for team_player, player in team_players:
            score = _calculate_player_score_in_time_range(
                session,
                player.player_name,
                start_ts,
                end_ts,
                use_best_2_of_3
            )
            total_team_score += score
            if score > top_player_score:
                top_player_score = score
                top_player_name = player.player_name

        average_score = total_team_score / starting_player_count if starting_player_count > 0 else 0.0

        team_responses.append(TeamScoreResponse(
            team_id=team.id,
            team_name=team.name,
            user_id=team.user_id,
            username=user_id_to_name.get(team.user_id),
            total_score=total_team_score,
            player_count=starting_player_count,
            average_player_score=average_score,
            top_player=top_player_name,
            top_player_score=top_player_score if top_player_score > 0 else None
        ))

    team_responses = _dedupe_team_scores_by_user(team_responses)
    team_responses.sort(key=lambda x: x.total_score, reverse=True)

    return LeagueLeaderboardResponse(
        league_id=league_id,
        league_name=league.name,
        teams=team_responses,
        last_updated=datetime.utcnow()
    )


@router.get("/leagues/{league_id}/leaderboard/season", response_model=LeagueLeaderboardResponse)
async def get_league_leaderboard_season(
    league_id: int,
    year: Optional[int] = Query(None, description="Season year (defaults to current year)"),
    session: Session = Depends(get_session)
):
    """
    Season leaderboard for a league across the specified year (default current year),
    summing starting player scores across all relevant matches.
    """
    league = session.exec(select(League).where(League.id == league_id)).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    now = datetime.now(timezone.utc)
    season_year = year or now.year
    season_start = datetime(season_year, 1, 1)
    start_ts = int(season_start.timestamp())
    end_ts = int(now.timestamp())

    teams = session.exec(select(Team).where(Team.league_id == league_id)).all()
    league_settings = session.exec(select(LeagueSettings).where(LeagueSettings.league_id == league_id)).first()
    use_best_2_of_3 = league_settings.use_best_2_of_3 if league_settings else True

    user_id_to_name = {}
    user_ids = [t.user_id for t in teams]
    if user_ids:
        users = session.exec(select(User).where(User.id.in_(user_ids))).all()
        user_id_to_name = {u.id: u.username for u in users}

    team_responses: list[TeamScoreResponse] = []
    for team in teams:
        team_players = session.exec(
            select(TeamPlayer, Players)
            .join(Players, TeamPlayer.player_name == Players.player_name)
            .where(and_(TeamPlayer.team_id == team.id, TeamPlayer.is_starting == True))
        ).all()

        total_team_score = 0.0
        starting_player_count = len(team_players)
        top_player_name = None
        top_player_score = 0.0

        for team_player, player in team_players:
            score = _calculate_player_score_in_time_range(
                session,
                player.player_name,
                start_ts,
                end_ts,
                use_best_2_of_3
            )
            total_team_score += score
            if score > top_player_score:
                top_player_score = score
                top_player_name = player.player_name

        average_score = total_team_score / starting_player_count if starting_player_count > 0 else 0.0

        team_responses.append(TeamScoreResponse(
            team_id=team.id,
            team_name=team.name,
            user_id=team.user_id,
            username=user_id_to_name.get(team.user_id),
            total_score=total_team_score,
            player_count=starting_player_count,
            average_player_score=average_score,
            top_player=top_player_name,
            top_player_score=top_player_score if top_player_score > 0 else None
        ))

    team_responses = _dedupe_team_scores_by_user(team_responses)
    team_responses.sort(key=lambda x: x.total_score, reverse=True)

    return LeagueLeaderboardResponse(
        league_id=league_id,
        league_name=league.name,
        teams=team_responses,
        last_updated=datetime.now(timezone.utc)
    )


@router.get("/teams/{team_id}/details", response_model=TeamDetailResponse)
async def get_team_details(
    team_id: int,
    event: Optional[str] = Query(None, description="Specific event to filter scores. If not provided, uses current event."),
    session: Session = Depends(get_session)
):
    """Get detailed information about a team including all player scores."""

    # Verify team exists
    team = session.exec(select(Team).where(Team.id == team_id)).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Determine which event to use
    if event is None:
        event = get_current_event(session)

    # Get all players on the team with their aggregated stats
    team_players = session.exec(
        select(TeamPlayer, Players)
        .join(Players, TeamPlayer.player_name == Players.player_name)
        .where(TeamPlayer.team_id == team_id)
    ).all()

    starting_players = []
    bench_players = []
    total_team_score = 0  # Only starting players contribute to team score

    # Get league settings to check if best 2 of 3 scoring is enabled
    league_settings = session.exec(
        select(LeagueSettings).where(LeagueSettings.league_id == team.league_id)
    ).first()
    use_best_2_of_3 = league_settings.use_best_2_of_3 if league_settings else True

    for team_player, player in team_players:
        # Calculate player stats using best 2 of 3 or traditional method
        player_data = calculate_player_score_with_best_2_of_3(
            player.player_name, 
            event, 
            session, 
            use_best_2_of_3
        )
        total_score = 0.0
        for m in player_data["match_breakdowns"]:
            total_score += _calculate_match_score_with_agent_predictions(
                session,
                team.id,
                player.player_name,
                m["match_id"],
                use_best_2_of_3,
            )
        total_kills = player_data["total_kills"]
        total_assists = player_data["total_assists"]
        total_deaths = player_data["total_deaths"]
        matches_played = player_data["matches_played"]
        average_score = player_data["average_score"]

        player_response = PlayerScoreResponse(
            player_name=player.player_name,
            total_score=total_score,
            total_kills=total_kills,
            total_assists=total_assists,
            total_deaths=total_deaths,
            matches_played=matches_played,
            average_score=average_score
        )

        # Separate starting and bench players
        if team_player.is_starting:
            starting_players.append(player_response)
            total_team_score += total_score  # Only starting players contribute to team score
        else:
            bench_players.append(player_response)

    # Sort both lists by total score descending
    starting_players.sort(key=lambda x: x.total_score, reverse=True)
    bench_players.sort(key=lambda x: x.total_score, reverse=True)
    
    # Get recent matches for STARTING players on this team
    starting_player_names = [player.player_name for player in starting_players]

    if starting_player_names:
        recent_matches_data = session.exec(
            select(Match, func.count(PlayerStat.id).label('team_players_in_match'))
            .join(PlayerStat, Match.id == PlayerStat.match_id)
            .where(
                and_(
                    PlayerStat.player_name.in_(starting_player_names),
                    Match.match_event == event
                )
            )
            .group_by(Match.id)
            .order_by(Match.unix_timestamp.desc())
            .limit(10)
        ).all()
    else:
        recent_matches_data = []

    recent_matches = []
    for match, team_players_count in recent_matches_data:
        recent_matches.append({
            "match_id": match.id,
            "team1": match.team1,
            "team2": match.team2,
            "match_event": match.match_event,
            "timestamp": match.unix_timestamp,
            "team_players_in_match": team_players_count
        })
    
    return TeamDetailResponse(
        team_id=team_id,
        team_name=team.name,
        user_id=team.user_id,
        total_score=total_team_score,  # Only starting players contribute
        starting_players=starting_players,
        bench_players=bench_players,
        recent_matches=recent_matches
    )


@router.get("/players/{player_name}/stats", response_model=PlayerScoreResponse)
async def get_player_stats(
    player_name: str,
    event: Optional[str] = Query(None, description="Specific event to filter scores. If not provided, uses current event."),
    session: Session = Depends(get_session),
    days: Optional[int] = Query(None, description="Limit stats to last N days"),
    use_best_2_of_3: Optional[bool] = Query(True, description="Use best 2 of 3 scoring method")
):
    """Get detailed statistics for a specific player."""

    # Determine which event to use
    if event is None:
        event = get_current_event(session)

    # If days filter is specified, we need to modify the event-based approach
    if days:
        # For days-based filtering, we'll calculate manually
        cutoff_timestamp = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
        
        # Get matches within the time range for this player
        matches = session.exec(
            select(Match.id, Match.match_event, Match.team1, Match.team2, Match.unix_timestamp)
            .join(PlayerStat, PlayerStat.match_id == Match.id)
            .where(
                and_(
                    PlayerStat.player_name == player_name,
                    Match.match_event == event,
                    Match.unix_timestamp >= cutoff_timestamp
                )
            )
            .distinct()
        ).all()
        
        total_score = 0.0
        total_kills = 0
        total_deaths = 0
        total_assists = 0
        
        for match in matches:
            if use_best_2_of_3:
                match_score = calculate_best_2_of_3_score(player_name, match.id, session)
            else:
                match_stats = session.exec(
                    select(func.sum(PlayerStat.score).label('total_score'))
                    .where(
                        and_(
                            PlayerStat.player_name == player_name,
                            PlayerStat.match_id == match.id
                        )
                    )
                ).first()
                match_score = float(match_stats.total_score or 0)
            
            # Get kills/deaths/assists for this match
            match_stats = session.exec(
                select(
                    func.sum(PlayerStat.kills).label('total_kills'),
                    func.sum(PlayerStat.assists).label('total_assists'),
                    func.sum(PlayerStat.deaths).label('total_deaths')
                )
                .where(
                    and_(
                        PlayerStat.player_name == player_name,
                        PlayerStat.match_id == match.id
                    )
                )
            ).first()
            
            total_score += match_score
            total_kills += int(match_stats.total_kills or 0)
            total_assists += int(match_stats.total_assists or 0)
            total_deaths += int(match_stats.total_deaths or 0)
        
        matches_played = len(matches)
        average_score = total_score / matches_played if matches_played > 0 else 0
        
        return PlayerScoreResponse(
            player_name=player_name,
            total_score=total_score,
            total_kills=total_kills,
            total_assists=total_assists,
            total_deaths=total_deaths,
            matches_played=matches_played,
            average_score=average_score
        )
    
    else:
        # Use the comprehensive calculation for event-based stats
        player_data = calculate_player_score_with_best_2_of_3(
            player_name, 
            event, 
            session, 
            use_best_2_of_3
        )
        
        if player_data["total_score"] == 0 and player_data["matches_played"] == 0:
            raise HTTPException(status_code=404, detail="Player not found or no stats available")

        return PlayerScoreResponse(
            player_name=player_name,
            total_score=player_data["total_score"],
            total_kills=player_data["total_kills"],
            total_assists=player_data["total_assists"],
            total_deaths=player_data["total_deaths"],
            matches_played=player_data["matches_played"],
            average_score=player_data["average_score"]
        )


@router.get("/players/{player_name}/detailed-stats", response_model=DetailedPlayerScoreResponse)
async def get_detailed_player_stats(
    player_name: str,
    event: Optional[str] = Query(None, description="Specific event to filter scores. If not provided, uses current event."),
    session: Session = Depends(get_session),
    use_best_2_of_3: Optional[bool] = Query(True, description="Use best 2 of 3 scoring method")
):
    """Get detailed statistics for a specific player including match and map breakdowns."""

    # Determine which event to use
    if event is None:
        event = get_current_event(session)

    # Use the comprehensive calculation with detailed breakdowns
    player_data = calculate_player_score_with_best_2_of_3(
        player_name, 
        event, 
        session, 
        use_best_2_of_3
    )
    
    if player_data["total_score"] == 0 and player_data["matches_played"] == 0:
        raise HTTPException(status_code=404, detail="Player not found or no stats available")

    return DetailedPlayerScoreResponse(
        player_name=player_name,
        total_score=player_data["total_score"],
        total_kills=player_data["total_kills"],
        total_assists=player_data["total_assists"],
        total_deaths=player_data["total_deaths"],
        matches_played=player_data["matches_played"],
        average_score=player_data["average_score"],
        match_breakdowns=player_data["match_breakdowns"],
        scoring_method=player_data["scoring_method"]
    )


@router.get("/players/{player_name}/maps/{match_id}", response_model=Dict[str, Any])
async def get_player_match_maps_breakdown(
    player_name: str,
    match_id: int,
    session: Session = Depends(get_session)
):
    """Get detailed map breakdown for a specific player in a specific match."""
    
    map_breakdown = get_player_map_breakdown(player_name, match_id, session)
    
    if map_breakdown["maps_played"] == 0:
        raise HTTPException(status_code=404, detail="No map data found for this player in this match")
    
    return map_breakdown


@router.get("/matches/live", response_model=List[LiveMatchResponse])
async def get_live_matches(session: Session = Depends(get_session)):
    """Get currently live matches with deduped live scores and players."""

    current_time = int(datetime.now(timezone.utc).timestamp())
    cutoff_time = current_time - 14400  # 4 hours ago

    # Order by most recent first so we can pick the latest per match
    live_rows = session.exec(
        select(Match, LiveScore)
        .join(LiveScore, Match.id == LiveScore.match_id)
        .where(
            and_(
                Match.unix_timestamp >= cutoff_time,
                Match.unix_timestamp <= current_time,
                or_(
                    Match.match_event.contains("VCT "),
                    Match.match_event.contains("Masters "),
                    Match.match_event.contains("Champions ")
                )
            )
        )
        .order_by(LiveScore.timestamp.desc())
    ).all()

    # Keep only the latest LiveScore per match
    latest_by_match: dict[int, tuple[Match, LiveScore]] = {}
    for match, live_score in live_rows:
        if match.id in latest_by_match:
            continue
        latest_by_match[match.id] = (match, live_score)

    live_matches: list[LiveMatchResponse] = []
    for match_id, (match, live_score) in latest_by_match.items():
        # Get player stats ordered by most recent (id desc) and dedupe by exact stat line to remove duplicates
        # This allows same player on different maps but removes exact duplicates
        players_data = session.exec(
            select(PlayerStat)
            .where(PlayerStat.match_id == match.id)
            .order_by(PlayerStat.score.desc())
        ).all()

        unique_players: dict[tuple[str, str | None, str | None, int, int, int], PlayerStat] = {}
        for player in players_data:
            # Dedupe key includes all stats to only remove exact duplicates
            key = (player.player_name, player.map_name, player.agent, player.kills, player.deaths, player.assists)
            if key in unique_players:
                continue
            unique_players[key] = player

        live_player_scores = [
            {
                "player_name": p.player_name,
                "map_name": p.map_name,
                "agent": p.agent,
                "kills": p.kills,
                "deaths": p.deaths,
                "assists": p.assists,
                "score": float(p.score or 0.0),
            }
            for p in unique_players.values()
        ]

        live_matches.append(
            LiveMatchResponse(
                match_id=match.id,
                team1=match.team1,
                team2=match.team2,
                current_map=live_score.current_map,
                team1_score=str(live_score.team1_score),
                team2_score=str(live_score.team2_score),
                live_player_scores=live_player_scores,
            )
        )

    return live_matches


@router.get("/matches", response_model=List[MatchStatusResponse])
async def get_matches_with_status(session: Session = Depends(get_session)):
    """Get matches with dynamic status based on current time and scraping activity."""

    current_time = int(datetime.now(timezone.utc).timestamp())
    four_hours_ago = current_time - (4 * 60 * 60)

    # Get all VCT matches from the last 4 hours onwards (no future limit)
    matches_data = session.exec(
        select(Match)
        .where(
            and_(
                or_(
                    Match.match_event.contains("VCT "),
                    Match.match_event.contains("Masters "),
                    Match.match_event.contains("Champions ")
                ),
                Match.unix_timestamp >= four_hours_ago
            )
        )
        .order_by(Match.unix_timestamp)
    ).all()

    match_responses = []
    seen_match_keys: set[str] = set()
    for match in matches_data:
        # Deduplicate by VLR match id when available, else by match_page
        dedupe_key = match.vlr_match_id or match.match_page or str(match.id)
        if dedupe_key in seen_match_keys:
            continue
        seen_match_keys.add(dedupe_key)
        # Calculate time until match
        time_until_match = match.unix_timestamp - current_time

        # Check if we have recent live data for this match
        recent_live_data = session.exec(
            select(LiveScore)
            .where(
                and_(
                    LiveScore.match_id == match.id,
                    LiveScore.timestamp >= datetime.now(timezone.utc) - timedelta(minutes=10)  # Last 10 minutes
                )
            )
            .limit(1)
        ).first()

        # Determine match status
        if recent_live_data:  # If we have recent live data, match is definitely live
            status = "live"
        elif time_until_match > 300:  # More than 5 minutes in future
            status = "upcoming"
        elif time_until_match > -14400:  # Started within 4 hours but no recent data
            status = "completed"
        else:  # More than 4 hours ago
            status = "completed"

        # Get the most recent scrape time
        last_live_score = session.exec(
            select(LiveScore)
            .where(LiveScore.match_id == match.id)
            .order_by(LiveScore.timestamp.desc())
            .limit(1)
        ).first()

        match_response = MatchStatusResponse(
            match_id=match.id,
            team1=match.team1,
            team2=match.team2,
            match_event=match.match_event,
            scheduled_time=match.unix_timestamp,
            status=status,
            time_until_match=time_until_match,
            match_page=match.match_page,
            last_scraped=last_live_score.timestamp if last_live_score else None,
            has_live_data=recent_live_data is not None
        )
        match_responses.append(match_response)

    return match_responses
