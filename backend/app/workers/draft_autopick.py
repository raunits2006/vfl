import logging
import random
import json
from datetime import datetime, timezone, timedelta
from sqlmodel import Session, select
from sqlalchemy import text
from app.celery_app import celery_app
from app.database import engine
from app.models.league_models import DraftSession, DraftPick, DraftStatus, Team, TeamPlayer, League, LeagueStatus
from app.models.player_pool_model import Players
from app.utils.draft_utils import (
    get_next_draft_state, get_draft_completion_info, calculate_snake_draft_user
)

logger = logging.getLogger(__name__)

# Draft configuration constants
DEFAULT_PICK_DEADLINE_MINUTES = 1

def _acquire_draft_lock(draft_id: int, session: Session, timeout_seconds: int = 30) -> bool:
    """
    Try to acquire a lock for a specific draft to prevent race conditions.
    Returns True if lock was acquired, False otherwise.
    """
    try:
        # Use PostgreSQL advisory lock (if using PostgreSQL)
        # For other databases, you might need a different approach
        result = session.execute(
            text("SELECT pg_try_advisory_lock(:lock_id)"),
            {"lock_id": draft_id}
        ).fetchone()

        if result and result[0]:
            logger.debug(f"Acquired lock for draft {draft_id}")
            return True
        else:
            logger.debug(f"Could not acquire lock for draft {draft_id} - already locked")
            return False

    except Exception as e:
        # If advisory locks aren't available, fall back to optimistic locking
        logger.warning(f"Advisory lock not available for draft {draft_id}, using optimistic locking: {e}")
        return True

def _release_draft_lock(draft_id: int, session: Session):
    """
    Release the lock for a specific draft.
    """
    try:
        session.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": draft_id}
        )
        logger.debug(f"Released lock for draft {draft_id}")
    except Exception as e:
        logger.warning(f"Could not release lock for draft {draft_id}: {e}")

def _perform_autopick(draft_id: int, session: Session, skip_deadline_check: bool = False):
    """
    Perform autopick for a draft that has exceeded its deadline.
    
    Args:
        draft_id: The ID of the draft to autopick for
        session: The database session
        skip_deadline_check: If True, skip the deadline check (used when called from make_pick
                            which already verified the deadline passed)
    """
    # Try to acquire lock to prevent race conditions
    if not _acquire_draft_lock(draft_id, session):
        logger.info(f"Draft {draft_id} is being processed by another worker")
        return False
    
    try:
        # Get the draft session
        draft = session.exec(select(DraftSession).where(DraftSession.id == draft_id)).first()
        if not draft or draft.status != DraftStatus.IN_PROGRESS:
            logger.warning(f"Draft {draft_id} not found or not in progress")
            return False
        
        # Get current timestamp (needed for pick and deadline updates)
        now = datetime.now(timezone.utc)
        
        # Check if deadline has passed (skip if called from make_pick)
        if not skip_deadline_check:
            pick_deadline = draft.pick_deadline
            if pick_deadline and pick_deadline.tzinfo is None:
                pick_deadline = pick_deadline.replace(tzinfo=timezone.utc)
            
            if not pick_deadline or now <= pick_deadline:
                logger.info(f"Draft {draft_id} deadline not exceeded yet")
                return False
        
        # Check if draft is complete using new logic
        total_picks_needed, is_complete = get_draft_completion_info(session, draft_id)
        if is_complete:
            logger.warning(f"Draft {draft_id} is complete")
            return False

        # Get current user using snake draft logic
        import json
        draft_order = json.loads(draft.draft_order)
        current_user_id, _ = calculate_snake_draft_user(
            draft.current_pick,
            draft_order,
            total_picks_needed
        )
        
        # Find the team for the current user
        team = session.exec(
            select(Team).where(
                Team.league_id == draft.league_id,
                Team.user_id == current_user_id
            )
        ).first()
        
        if not team:
            logger.error(f"No team found for user {current_user_id} in draft {draft_id}")
            return False
        
        # Get available players
        available_players = session.exec(select(Players)).all()
        picked_players = session.exec(
            select(DraftPick).where(DraftPick.draft_session_id == draft_id)
        ).all()
        picked_names = {p.player_name for p in picked_players}
        remaining = [p for p in available_players if p.player_name not in picked_names]
        
        # Note: Duelist filtering removed since primary_role field no longer exists in Players model
        
        if not remaining:
            logger.error(f"No eligible players left to autopick for draft {draft_id}")
            return False
        
        # Simple autopick strategy: pick random available player
        autopick_player = remaining[random.randint(0, len(remaining) - 1)]
        
        # Create the pick
        pick = DraftPick(
            draft_session_id=draft_id,
            team_id=team.id,
            player_name=autopick_player.player_name,
            pick_number=draft.current_pick,
            picked_at=now
        )
        session.add(pick)
        
        # Add player to team roster
        team_player = TeamPlayer(
            team_id=team.id,
            player_name=autopick_player.player_name,
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
            # Mark league as ACTIVE when draft completes
            league = session.exec(select(League).where(League.id == draft.league_id)).first()
            if league:
                league.status = LeagueStatus.ACTIVE
                if hasattr(league, "updated_at"):
                    league.updated_at = now
                session.add(league)
        else:
            draft.current_user_id = next_user_id
            draft.pick_deadline = datetime.now(timezone.utc) + timedelta(minutes=DEFAULT_PICK_DEADLINE_MINUTES)
        
        session.add(draft)
        session.commit()
        
        logger.info(f"Autopick completed for draft {draft_id}: {autopick_player.player_name} picked for team {team.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error performing autopick for draft {draft_id}: {e}", exc_info=True)
        session.rollback()
        return False
    finally:
        # Always release the lock
        _release_draft_lock(draft_id, session)

@celery_app.task(name="app.workers.draft_autopick.check_expired_picks", bind=True, max_retries=3, default_retry_delay=30)
def check_expired_picks_task(self):
    """
    Celery task to check for expired draft picks and perform autopicks.
    Runs every minute to check for drafts that need autopicking.
    """
    logger.info("Checking for expired draft picks...")
    
    try:
        # Get all in-progress drafts first
        with Session(engine) as session:
            in_progress_drafts = session.exec(
                select(DraftSession).where(DraftSession.status == DraftStatus.IN_PROGRESS)
            ).all()
        
        autopicks_performed = 0
        failed_drafts = []
        
        # Process each draft with its own session to avoid conflicts
        for draft in in_progress_drafts:
            try:
                with Session(engine) as draft_session:
                    if _perform_autopick(draft.id, draft_session):
                        autopicks_performed += 1
                        logger.info(f"Successfully processed autopick for draft {draft.id}")
                    else:
                        logger.debug(f"No autopick needed for draft {draft.id}")
            except Exception as e:
                logger.error(f"Failed to process autopick for draft {draft.id}: {e}", exc_info=True)
                failed_drafts.append(draft.id)
        
        logger.info(f"Autopick check completed. {autopicks_performed} autopicks performed.")
        if failed_drafts:
            logger.warning(f"Failed to process drafts: {failed_drafts}")
            
    except Exception as exc:
        logger.error(f"Error in check_expired_picks_task: {exc}", exc_info=True)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.critical("Max retries exceeded for check_expired_picks_task")
        except Exception as retry_exc:
            logger.error(f"Failed to schedule retry for check_expired_picks_task: {retry_exc}", exc_info=True)

@celery_app.task(name="app.workers.draft_autopick.process_single_draft", bind=True, max_retries=3, default_retry_delay=30)
def process_single_draft_task(self, draft_id: int):
    """
    Celery task to process autopick for a single specific draft.
    This can be used to handle individual drafts or for testing.
    """
    logger.info(f"Processing autopick for draft {draft_id}")
    
    try:
        with Session(engine) as session:
            success = _perform_autopick(draft_id, session)
            if success:
                logger.info(f"Successfully processed autopick for draft {draft_id}")
                return {"draft_id": draft_id, "status": "success", "autopick_performed": True}
            else:
                logger.info(f"No autopick needed for draft {draft_id}")
                return {"draft_id": draft_id, "status": "success", "autopick_performed": False}
                
    except Exception as exc:
        logger.error(f"Error processing autopick for draft {draft_id}: {exc}", exc_info=True)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.critical(f"Max retries exceeded for draft {draft_id}")
            return {"draft_id": draft_id, "status": "failed", "error": str(exc)}
        except Exception as retry_exc:
            logger.error(f"Failed to schedule retry for draft {draft_id}: {retry_exc}", exc_info=True)
            return {"draft_id": draft_id, "status": "failed", "error": str(retry_exc)} 