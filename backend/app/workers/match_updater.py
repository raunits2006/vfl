import asyncio
from typing import Optional
import httpx
from sqlmodel import Session, select
import logging
import re
from sqlalchemy import or_, and_

from app.celery_app import celery_app
from app.core.config import settings
from app.database import engine # Ensure 'engine' is defined and importable from app.database
from app.models.match_model import Match, MatchCreate
from datetime import datetime, timezone, timedelta
from app.workers.live_match_scraper import scrape_live_match_data

# Get a logger for this module
logger = logging.getLogger(__name__)

def _extract_vlr_match_id(match_page_url: Optional[str]) -> Optional[str]:
    if not match_page_url:
        return None
    match = re.search(r'\/(\d+)', match_page_url)
    if match:
        return match.group(1)
    logger.warning(f"Could not extract match ID from URL: {match_page_url}")
    return None


async def _fetch_and_process_matches_logic(session: Session):
    """
    Core asynchronous logic for fetching upcoming matches from VLR API
    and updating the database.
    """
    logger.info(f"Fetching upcoming matches from: {settings.VLR_API_UPCOMING_MATCHES_URL}")
    processed_count = 0
    created_count = 0
    updated_count = 0

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(settings.VLR_API_UPCOMING_MATCHES_URL)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
            raw_data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error {exc.response.status_code} from VLR API: {exc.request.url!r} - Response: {exc.response.text}")
            raise  # Propagate to Celery task for failure handling
        except httpx.RequestError as exc:
            logger.error(f"Request error connecting to VLR API: {exc.request.url!r}")
            raise  # Propagate to Celery task for failure handling
        except Exception as exc:
            logger.error(f"Unexpected error during API call or JSON parsing: {str(exc)}")
            raise

    match_list = raw_data.get("data", {}).get("segments", [])
    if not isinstance(match_list, list):
        logger.warning(f"Expected a list of matches, but found type: {type(match_list)}. Raw data snippet: {str(raw_data)[:200]}")
        return # Stop processing if the structure is not as expected

    # Always merge in live matches so we don't miss in-progress games
    try:
        async with httpx.AsyncClient() as client:
            live_resp = await client.get(settings.VLR_API_LIVE_SCORE_URL)
            live_resp.raise_for_status()
            live_raw = live_resp.json()
            live_list = live_raw.get("data", {}).get("segments", [])
            if isinstance(live_list, list) and live_list:
                logger.info(f"Merging {len(live_list)} live matches from live_score endpoint")
                match_list = (match_list or []) + live_list
    except Exception as exc:
        logger.error(f"Failed to fetch live matches for merge: {exc}")

    # Deduplicate by VLR match id to avoid double-processing when merging
    seen_vlr_ids: set[str] = set()
    for match_item in match_list:
        if not isinstance(match_item, dict):
            logger.warning(f"Skipping non-dict match item: {match_item}")
            continue

        match_page_url = match_item.get("match_page")
        if not match_page_url:
            logger.warning(f"Match item missing 'match_page', skipping: {match_item}")
            continue

        vlr_id = _extract_vlr_match_id(match_page_url)
        logger.info(f"Extracted VLR ID: {vlr_id} from URL: {match_page_url}")
        if not vlr_id:
            logger.warning(f"Skipping match item with invalid URL: {match_page_url}")
            continue
        if vlr_id in seen_vlr_ids:
            continue
        seen_vlr_ids.add(vlr_id)

        try:
            # Prepare data for MatchCreate model
            match_data = MatchCreate(
                team1=match_item.get("team1"),
                team2=match_item.get("team2"),
                match_series=match_item.get("match_series"),
                match_event=match_item.get("match_event"),
                unix_timestamp=match_item.get("unix_timestamp"),
                match_page=match_page_url,
                vlr_match_id=vlr_id
            )

            # Upsert logic: Check if match exists by match_page
            statement = select(Match).where(Match.vlr_match_id == vlr_id)
            db_match = session.exec(statement).first()

            if db_match:
                logger.debug(f"Updating match (VLR ID: {vlr_id})")
                for key, value in match_data.model_dump(exclude_unset=True).items():
                    setattr(db_match, key, value)
                session.add(db_match)
                updated_count += 1
            else:
                logger.debug(f"Creating new match: {match_page_url}")
                db_match = Match.model_validate(match_data) # Use model_validate for SQLModel table models
                session.add(db_match)
                created_count += 1
            processed_count += 1
        except Exception as e:
            logger.error(f"Error processing match item {match_page_url or str(match_item)[:100]}: {e}", exc_info=True)
            # Continue with the next item if one fails
            continue

    if processed_count > 0:
        try:
            session.commit()
            logger.info(f"Database commit successful. Processed: {processed_count}, Created: {created_count}, Updated: {updated_count}")
        except Exception as e:
            logger.error(f"Database commit failed: {e}", exc_info=True)
            session.rollback()
            raise # Propagate to Celery task
    else:
        logger.info("No match data was processed or changed that required a commit.")

    # For any live matches we just upserted, trigger scraping immediately
    try:
        now = int(datetime.now(timezone.utc).timestamp())
        live_candidates = session.exec(
            select(Match).where(
                and_(
                    Match.unix_timestamp >= now - 14400,
                    Match.unix_timestamp <= now + 3600,
                    or_(
                        Match.match_event.contains("VCT "),
                        Match.match_event.contains("Masters "),
                        Match.match_event.contains("Champions "),
                        Match.match_series.contains("VCT "),
                        Match.match_series.contains("Masters "),
                        Match.match_series.contains("Champions ")
                    )
                )
            )
        ).all()
        for m in live_candidates:
            scrape_live_match_data.delay(m.id)
        if live_candidates:
            logger.info(f"Triggered scraping for {len(live_candidates)} live candidate matches after updater run.")
    except Exception as e:
        logger.error(f"Failed to trigger scraping after updater: {e}")


@celery_app.task(name="app.workers.match_updater.update_upcoming_matches_task", bind=True, max_retries=3, default_retry_delay=60 * 5) # Retry after 5 mins
def update_upcoming_matches_task(self): # 'self' is bound to the task instance
    """
    Celery task to periodically fetch upcoming matches from VLR.gg API
    and update the database.
    """
    logger.info(f"Executing Celery task: update_upcoming_matches_task (Attempt {self.request.retries + 1} of {self.max_retries + 1 if self.max_retries is not None else 'N/A'})")
    try:
        # Each task execution gets its own database session
        with Session(engine) as session:
            asyncio.run(_fetch_and_process_matches_logic(session))
        logger.info("update_upcoming_matches_task finished successfully.")
    except Exception as exc:
        logger.error(f"Error in update_upcoming_matches_task: {exc}", exc_info=True)
        try:
            # Retry the task. Celery handles the backoff and max_retries.
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.critical(f"Max retries exceeded for update_upcoming_matches_task. Failing permanently for this run.")
            # Optionally, send a notification here (e.g., email, Slack)
        except Exception as retry_exc: # Catch potential errors during retry call itself
            logger.error(f"Failed to schedule retry for update_upcoming_matches_task: {retry_exc}", exc_info=True)


@celery_app.task(name="app.workers.maybe_trigger_scrape_live_matches", bind=True, max_retries=3, default_retry_delay=60 * 5)
def maybe_trigger_scrape_live_matches(self):
    """
    Celery task to check if there are any live VCT matches and trigger scraping if so.
    """
    now = int(datetime.now(timezone.utc).timestamp())
    with Session(engine) as session:
        # Consider matches that could be live: started within last 4 hours OR starting within next hour
        statement = select(Match).where(
            and_(
                Match.unix_timestamp >= now - 14400,  # started within last 4 hours
                Match.unix_timestamp <= now + 3600,   # OR starting within next hour (matches can start early)
                or_(
                    Match.match_event.contains("VCT "),
                    Match.match_event.contains("Masters "),
                    Match.match_event.contains("Champions ")
                )
            )
        )
        live_matches = session.exec(statement).all()
        if not live_matches:
            logger.info("No live matches found in DB; attempting to backfill from live_score API and retry.")
            try:
                asyncio.run(_fetch_and_process_matches_logic(session))
            except Exception as exc:
                logger.error(f"Backfill from live_score failed: {exc}")
            # Re-check after backfill
            live_matches = session.exec(statement).all()
        if live_matches:
            logger.info(f"Found {len(live_matches)} live matches. Triggering scraping task.")
            scrape_live_matches_task.delay()
        else:
            logger.info("Still no live matches after backfill attempt.")

@celery_app.task(name="app.workers.update_live_matches", bind=True, max_retries=3, default_retry_delay=60 * 5)
def scrape_live_matches_task(self):
    """
    Celery task to find currently live VCT matches and trigger scraping for each.
    Only scrapes matches that are still ongoing (within 4 hours of start).
    """
    now = int(datetime.now(timezone.utc).timestamp())
    with Session(engine) as session:
        # Consider matches that could be live: started within last 4 hours OR starting within next hour
        statement = select(Match).where(
            and_(
                Match.unix_timestamp >= now - 14400,  # started within last 4 hours
                Match.unix_timestamp <= now + 3600,   # OR starting within next hour (matches can start early)
                or_(
                    Match.match_event.contains("VCT "),
                    Match.match_event.contains("Masters "),
                    Match.match_event.contains("Champions ")
                )
            )
        )
        live_matches = session.exec(statement).all()
        if not live_matches:
            logger.info("No live matches found to scrape.")
        for match in live_matches:
            # Optionally, check if already scraped recently to avoid duplicates
            scrape_live_match_data.delay(match.id)

