"""
Utility functions for draft logic, including snake draft calculations.
"""
import json
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional
from sqlmodel import Session, select
from app.models.league_models import DraftSession, LeagueSettings, Team
from app.models.match_model import Match
from fastapi import HTTPException, status


def calculate_snake_draft_user(
    pick_number: int, 
    draft_order: List[int], 
    total_picks: int
) -> Tuple[int, int]:
    """
    Calculate which user should pick for a given pick number in a snake draft.
    
    Args:
        pick_number: The current pick number (1-based)
        draft_order: List of user IDs in the original draft order
        total_picks: Total number of picks in the draft
    
    Returns:
        Tuple of (user_id, pick_index_in_order)
        
    Example for 3 teams [A, B, C] with 2 rounds:
        Pick 1: A (index 0)  # Round 1: A -> B -> C
        Pick 2: B (index 1)
        Pick 3: C (index 2)
        Pick 4: C (index 2)  # Round 2: C -> B -> A (reversed)
        Pick 5: B (index 1)
        Pick 6: A (index 0)
    """
    if not draft_order or pick_number < 1:
        raise ValueError("Invalid draft order or pick number")
    
    num_teams = len(draft_order)
    
    # Convert to 0-based indexing for calculations
    pick_index = pick_number - 1
    
    # Calculate which round we're in (0-based)
    round_number = pick_index // num_teams
    
    # Calculate position within the round (0-based)
    position_in_round = pick_index % num_teams
    
    # For even rounds (0, 2, 4...), use normal order
    # For odd rounds (1, 3, 5...), use reversed order
    if round_number % 2 == 0:
        # Normal order
        user_index = position_in_round
    else:
        # Reversed order
        user_index = num_teams - 1 - position_in_round
    
    return draft_order[user_index], user_index


def get_draft_completion_info(session: Session, draft_id: int) -> Tuple[int, bool]:
    """
    Get information about draft completion status.
    
    Args:
        session: Database session
        draft_id: ID of the draft session
    
    Returns:
        Tuple of (total_picks_needed, is_complete)
    """
    # Get draft session
    draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")
    
    # Get league settings
    settings = session.exec(
        select(LeagueSettings).where(LeagueSettings.league_id == draft.league_id)
    ).first()
    if not settings:
        raise ValueError(f"League settings not found for league {draft.league_id}")
    
    # Parse draft order
    if not draft.draft_order:
        raise ValueError(f"Draft order not set for draft {draft_id}")
    
    draft_order = json.loads(draft.draft_order)
    num_teams = len(draft_order)
    
    # Calculate total picks needed
    total_picks_needed = num_teams * settings.max_players
    
    # Check if draft is complete
    is_complete = draft.current_pick > total_picks_needed
    
    return total_picks_needed, is_complete


def get_next_draft_state(
    session: Session, 
    draft_id: int, 
    current_pick: int
) -> Tuple[Optional[int], bool]:
    """
    Calculate the next draft state after a pick is made.
    
    Args:
        session: Database session
        draft_id: ID of the draft session
        current_pick: The pick number that was just made
    
    Returns:
        Tuple of (next_user_id, is_draft_complete)
    """
    total_picks_needed, _ = get_draft_completion_info(session, draft_id)
    
    # Get draft session
    draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
    if not draft:
        raise ValueError(f"Draft {draft_id} not found")
    
    draft_order = json.loads(draft.draft_order)
    
    # Calculate next pick number
    next_pick = current_pick + 1
    
    # Check if draft is complete
    if next_pick > total_picks_needed:
        return None, True
    
    # Calculate next user
    next_user_id, _ = calculate_snake_draft_user(next_pick, draft_order, total_picks_needed)
    
    return next_user_id, False


def get_free_agents_for_league(session: Session, league_id: int) -> List:
    """
    Get all players that are available as free agents for a specific league.
    Free agents are players that are not currently on any team in the league.
    
    Args:
        session: Database session
        league_id: ID of the league
    
    Returns:
        List of Players that are free agents
    """
    from app.models.league_models import TeamPlayer
    from app.models.player_pool_model import Players
    
    # Get all players currently on teams in this league
    drafted_players_query = session.exec(
        select(TeamPlayer.player_name)
        .join(Team, Team.id == TeamPlayer.team_id)
        .where(Team.league_id == league_id)
    )
    
    # Convert to set of player names (not tuple objects)
    drafted_names = {player_name for player_name in drafted_players_query}
    
    # Get all eligible players and filter out those already drafted
    all_players = session.exec(select(Players)).all()
    free_agents = [p for p in all_players if p.player_name not in drafted_names]
    
    return free_agents


def validate_free_agent_swap(
    session: Session, 
    team_id: int, 
    drop_player_name: str, 
    add_player_name: str
) -> tuple[bool, str]:
    """
    Validate that a free agent swap doesn't violate team rules.
    
    Note: Duelist player role restriction removed - only agent prediction duelist limit applies now.
    
    Args:
        session: Database session
        team_id: ID of the team making the swap
        drop_player_name: Name of player being dropped
        add_player_name: Name of player being added
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    from app.models.player_pool_model import Players
    from app.models.league_models import TeamPlayer
    
    # Check if the player being dropped is actually on the team
    current_player = session.exec(
        select(TeamPlayer).where(
            TeamPlayer.team_id == team_id,
            TeamPlayer.player_name == drop_player_name
        )
    ).first()
    
    if not current_player:
        return False, f"Player {drop_player_name} is not on your team"
    
    # Get both players to verify they exist
    drop_player = session.exec(select(Players).where(Players.player_name == drop_player_name)).first()
    add_player = session.exec(select(Players).where(Players.player_name == add_player_name)).first()
    
    if not drop_player or not add_player:
        return False, "One or both players not found"
    
    return True, ""


def perform_free_agent_swap(
    session: Session,
    team_id: int,
    league_id: int,
    drop_player_name: str,
    add_player_name: str
) -> bool:
    """
    Perform a free agent swap transaction atomically.
    
    Args:
        session: Database session
        team_id: ID of the team
        league_id: ID of the league
        drop_player_name: Name of player being dropped
        add_player_name: Name of player being added
    
    Returns:
        True if successful, False otherwise
    """
    from app.models.league_models import TeamPlayer, FreeAgentTransaction
    
    try:
        # Remove the dropped player from team
        drop_team_player = session.exec(
            select(TeamPlayer).where(
                TeamPlayer.team_id == team_id,
                TeamPlayer.player_name == drop_player_name
            )
        ).first()
        
        if drop_team_player:
            session.delete(drop_team_player)
        
        # Add the new player to team
        new_team_player = TeamPlayer(
            team_id=team_id,
            player_name=add_player_name,
            is_starting=False  # New players start on bench
        )
        session.add(new_team_player)
        
        # Record the transactions
        now = datetime.now(timezone.utc)
        
        # Drop transaction
        drop_transaction = FreeAgentTransaction(
            league_id=league_id,
            team_id=team_id,
            player_name=drop_player_name,
            transaction_type="drop",
            transaction_date=now
        )
        session.add(drop_transaction)
        
        # Add transaction
        add_transaction = FreeAgentTransaction(
            league_id=league_id,
            team_id=team_id,
            player_name=add_player_name,
            transaction_type="add",
            transaction_date=now
        )
        session.add(add_transaction)
        
        return True
        
    except Exception as e:
        # Let the caller handle the rollback
        raise e


def check_team_lock_status(session: Session) -> tuple[bool, str, Optional[datetime]]:
    """
    Check if teams are locked based on weekly schedule.
    Teams unlock every Monday at 12:00 AM CST and lock every Wednesday at 11:00 AM CST.
    
    Args:
        session: Database session
    
    Returns:
        Tuple of (is_locked, reason_message, next_unlock_or_lock_time)
    """
    # DEVELOPMENT MODE: Always return unlocked for development
    # TODO: Remove this when ready for production
    return False, "Team changes are currently unlocked (development mode).", None
    
    # Original lock logic commented out for development:
    # import pytz
    # 
    # # Define CST timezone
    # cst = pytz.timezone('America/Chicago')
    # 
    # # Get current time in CST
    # now_utc = datetime.now(timezone.utc)
    # now_cst = now_utc.astimezone(cst)
    # 
    # # Get current week's Monday 12:00 AM CST and Wednesday 11:00 AM CST
    # current_monday = now_cst.date() - timedelta(days=now_cst.weekday())
    # current_wednesday = current_monday + timedelta(days=2)
    # 
    # # Monday 12:00 AM CST (start of Monday)
    # unlock_time_cst = datetime.combine(current_monday, datetime.min.time())
    # # Wednesday 11:00 AM CST
    # lock_time_cst = datetime.combine(current_wednesday, datetime.min.time().replace(hour=11))
    # 
    # # Localize to CST timezone
    # unlock_time_cst = cst.localize(unlock_time_cst)
    # lock_time_cst = cst.localize(lock_time_cst)
    # 
    # # Convert to UTC for consistent comparison
    # unlock_time_utc = unlock_time_cst.astimezone(timezone.utc)
    # lock_time_utc = lock_time_cst.astimezone(timezone.utc)
    # 
    # # Determine if we're in the locked period
    # if now_utc >= lock_time_utc:
    #     # We're past Wednesday 11 AM, locked until next Monday 12:00 AM
    #     next_monday = current_monday + timedelta(days=7)
    #     next_unlock_time_cst = datetime.combine(next_monday, datetime.min.time())
    #     next_unlock_time_cst = cst.localize(next_unlock_time_cst)
    #     next_unlock_time_utc = next_unlock_time_cst.astimezone(timezone.utc)
    #     
    #     time_until_unlock = next_unlock_time_utc - now_utc
    #     days_until = time_until_unlock.days
    #     hours_until = int(time_until_unlock.seconds / 3600)
    #     
    #     message = (
    #         f"Team changes are locked. Teams are locked from Wednesday 11:00 AM CST "
    #         f"until Monday 12:00 AM CST. Next unlock in {days_until} days and {hours_until} hours "
    #         f"on {next_unlock_time_cst.strftime('%A, %B %d at %I:%M %p CST')}."
    #     )
    #     
    #     return True, message, next_unlock_time_utc
    #     
    # elif now_utc >= unlock_time_utc:
    #     # We're between Monday 12:00 AM and Wednesday 11:00 AM, unlocked
    #     time_until_lock = lock_time_utc - now_utc
    #     hours_until = int(time_until_lock.total_seconds() / 3600)
    #     
    #     message = f"Team changes are unlocked until {lock_time_cst.strftime('%A, %B %d at %I:%M %p CST')} (in {hours_until} hours)."
    #     
    #     return False, message, lock_time_utc
    #     
    # else:
    #     # We're before Monday 12:00 AM this week, still locked from last week
    #     time_until_unlock = unlock_time_utc - now_utc
    #     hours_until = int(time_until_unlock.total_seconds() / 3600)
    #     
    #     message = (
    #         f"Team changes are locked. Teams unlock every Monday at 12:00 AM CST. "
    #         f"Next unlock in {hours_until} hours on {unlock_time_cst.strftime('%A, %B %d at %I:%M %p CST')}."
    #     )
    #     
    #     return True, message, unlock_time_utc


def validate_team_not_locked(session: Session) -> None:
    """
    Validate that teams are not currently locked based on weekly schedule.
    Teams are locked from Wednesday 11:00 AM CST until Monday 12:00 AM CST.
    Raises HTTPException if teams are locked.
    
    Args:
        session: Database session
        
    Raises:
        HTTPException: If teams are locked based on weekly schedule
    """
    is_locked, message, _ = check_team_lock_status(session)
    if is_locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def validate_current_picker(
    session: Session,
    draft_id: int,
    expected_user_id: int
) -> bool:
    """
    Validate that the expected user is the correct current picker.
    
    Args:
        session: Database session
        draft_id: ID of the draft session
        expected_user_id: The user ID that should be picking
    
    Returns:
        True if the user is the correct current picker
    """
    # Get draft session
    draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
    if not draft:
        return False
    
    if not draft.draft_order:
        return False
    
    draft_order = json.loads(draft.draft_order)
    total_picks_needed, is_complete = get_draft_completion_info(session, draft_id)
    
    if is_complete:
        return False
    
    # Calculate who should be picking for the current pick
    current_user_id, _ = calculate_snake_draft_user(
        draft.current_pick, 
        draft_order, 
        total_picks_needed
    )
    
    return current_user_id == expected_user_id
