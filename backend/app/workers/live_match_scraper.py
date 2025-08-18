import httpx
from bs4 import BeautifulSoup
from sqlmodel import Session, select, and_
import logging
import re
import asyncio # For the main task execution
from datetime import datetime, timezone

from app.celery_app import celery_app
from app.core.config import settings
from app.database import engine # Ensure 'engine' is defined
from app.models.match_model import Match
from app.models.live_data_models import LiveScore, MapRound, PlayerStat

logger = logging.getLogger(__name__)

async def _scrape_live_match_data(match_page_url: str):
    """
    Main async function logic for scraping live match data.
    """

    logger.info(f"Starting live scrape for match page: {match_page_url}")
    live_data = {}

    async with httpx.AsyncClient(timeout=30.0) as client: 
        try:
            response = await client.get(match_page_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')  # scraping tool

            match_id_match = re.search(r'\/(\d+)', match_page_url)
            match_id = match_id_match.group(1) if match_id_match else None

            #current map/score scrape
            active_map = soup.select_one('.vm-stats-game.mod-active .map')
            if not active_map:
                logger.info(f"No active map found for match {match_page_url} - match may not be live")
                return None

            current_map = re.sub(r"PICK\S+|\-|\d\S+", '', active_map.get_text(strip=True))

            current_team1_score_elem = soup.select_one('.vm-stats-game.mod-active .team .score')
            current_team2_score_elem = soup.select_one('.vm-stats-game.mod-active .team.mod-right .score')

            if not current_team1_score_elem or not current_team2_score_elem:
                logger.info(f"No active scores found for match {match_page_url} - match may not be live")
                return None

            current_team1_score = current_team1_score_elem.get_text(strip=True)
            current_team2_score = current_team2_score_elem.get_text(strip=True)
            live_data['live_score'] = {
                'team1_score': current_team1_score,
                'team2_score': current_team2_score,
                'current_map': current_map,
                'match_id': match_id
            }

            
            #game score scraper
            map_rounds = []
            container = soup.select_one('.vm-stats-container')
            if container:
                for game in container.select('.vm-stats-game:not([data-game-id="all"])'):
                    if game.select_one('.team .score').get_text(strip=True) == '0' and game.select_one('.team.mod-right .score').get_text(strip=True) == '0':
                        continue
                    map_name = re.sub(r'PICK\S+|\-', '',game.select_one('.vm-stats-game-header .map').get_text(strip=True))
                    t1_rounds = game.select_one('.team .score').get_text(strip=True)
                    t2_rounds = game.select_one('.team.mod-right .score').get_text(strip=True)
                    t1_attack_rounds = game.select_one('.vm-stats-game-header .team span.mod-t').get_text(strip=True)
                    t1_defense_rounds= game.select_one('.vm-stats-game-header .team span.mod-ct').get_text(strip=True)
                    t2_attack_rounds = game.select_one('.vm-stats-game-header .team.mod-right span.mod-t').get_text(strip=True)
                    t2_defense_rounds = game.select_one('.vm-stats-game-header .team.mod-right span.mod-ct').get_text(strip=True)
                    map_rounds.append({
                        'map_name': map_name,
                        'team1_rounds': t1_rounds,
                        'team2_rounds': t2_rounds,
                        'team1_attack_rounds': t1_attack_rounds,
                        'team1_defense_rounds': t1_defense_rounds,
                        'team2_attack_rounds': t2_attack_rounds,
                        'team2_defense_rounds': t2_defense_rounds
                    })
                    
                live_data['map_rounds'] = map_rounds

                
            if container:
                players = []
                games_found = container.select('.vm-stats-game:not([data-game-id="all"])')
                logger.info(f"Found {len(games_found)} games to process for match {match_id}")

                for game_idx, game in enumerate(games_found):
                    # Get the map name for this game
                    map_elem = game.select_one('.vm-stats-game-header .map')
                    if not map_elem:
                        logger.warning(f"No map element found for game {game_idx + 1}, skipping")
                        continue

                    raw_map_text = map_elem.get_text(strip=True)
                    # Clean map name by removing common suffixes and timestamps
                    map_name = re.sub(r'(PICK.*|\-.*|\d+:\d+.*)', '', raw_map_text).strip()
                    # Remove extra whitespace
                    map_name = re.sub(r'\s+', ' ', map_name).strip()
                    # Fallback to original if cleaning resulted in empty string
                    map_name = map_name if map_name else raw_map_text
                    logger.info(f"Processing game {game_idx + 1}: {map_name}")

                    # Try multiple approaches to find all player rows
                    all_rows = []

                    # Approach 1: Look for all tables with player stats
                    all_tables = game.select('table.mod-overview')
                    logger.info(f"Found {len(all_tables)} stats tables for map {map_name}")

                    for table_idx, table in enumerate(all_tables):
                        tbody_elements = table.select('tbody')
                        logger.info(f"Table {table_idx + 1}: Found {len(tbody_elements)} tbody elements")

                        for tbody_idx, tbody in enumerate(tbody_elements):
                            tbody_rows = tbody.select('tr')
                            logger.info(f"Table {table_idx + 1}, Tbody {tbody_idx + 1}: Found {len(tbody_rows)} rows")
                            all_rows.extend(tbody_rows)

                    # Approach 2: If we still only have 5 rows, try looking for all player rows in the game container
                    if len(all_rows) <= 5:
                        logger.info(f"Only found {len(all_rows)} rows with table approach, trying broader search...")
                        broader_rows = game.select('tr')
                        logger.info(f"Found {len(broader_rows)} total rows in game container")

                        # Filter for rows that look like player stats (have player name and stats)
                        player_rows = []
                        for row in broader_rows:
                            name_elem = row.select_one('.mod-player .text-of')
                            kills_elem = row.select_one('.mod-vlr-kills .side.mod-both')
                            if name_elem and kills_elem:
                                player_rows.append(row)

                        logger.info(f"Found {len(player_rows)} player rows with broader search")
                        if len(player_rows) > len(all_rows):
                            all_rows = player_rows

                    logger.info(f"Final total player rows for map {map_name}: {len(all_rows)}")

                    if all_rows:
                        for row_idx, row in enumerate(all_rows):
                            name = row.select_one('.mod-player .text-of')
                            kills = row.select_one('.mod-vlr-kills .side.mod-both')
                            assists = row.select_one('.mod-vlr-assists .side.mod-both')
                            deaths = row.select_one('.mod-vlr-deaths .side.mod-both')
                            agent_class = row.select_one('.mod-agents')
                            agent_img = agent_class.find('img') if agent_class else None
                            agent = agent_img.get('title') if agent_img else None

                            player_name = name.get_text(strip=True) if name else "Unknown"
                            logger.info(f"Row {row_idx + 1}: Player={player_name}, Agent={agent}, K/D/A={kills.get_text(strip=True) if kills else 'N/A'}/{deaths.get_text(strip=True) if deaths else 'N/A'}/{assists.get_text(strip=True) if assists else 'N/A'}")

                            if name and agent and kills and deaths and assists:
                                kills_val = kills.get_text(strip=True)
                                assists_val = assists.get_text(strip=True)
                                deaths_val = deaths.get_text(strip=True)
                                if kills_val != "" and deaths_val != "" and assists_val != "":
                                    players.append({
                                        'match_id': match_id,
                                        'map_name': map_name,
                                        'player_name': player_name,
                                        'agent': agent,
                                        'kills': kills_val,
                                        'deaths': deaths_val,
                                        'assists': assists_val,
                                    })
                                    logger.info(f"Added player {player_name} to players list")
                                else:
                                    logger.warning(f"Skipping player {player_name} due to empty stats")
                            else:
                                logger.warning(f"Skipping row {row_idx + 1} due to missing elements: name={name is not None}, agent={agent is not None}, kills={kills is not None}, deaths={deaths is not None}, assists={assists is not None}")
                    else:
                        logger.warning(f"No player rows found for map {map_name}")

                logger.info(f"Total players extracted: {len(players)}")
                live_data['players'] = players


            return live_data        
                    
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error {exc.response.status_code} from {match_page_url}: {exc.request.url!r}")
            return None # Or raise to retry
        except httpx.RequestError as exc:
            logger.error(f"Request error for {match_page_url}: {exc.request.url!r}")
            return None # Or raise to retry
        except Exception as exc:
            logger.error(f"Unexpected error scraping {match_page_url}: {str(exc)}")
            return None # Or raise to retry


def fix_incomplete_match_scores(session, match_id: int, live_data: dict):
    """
    Detect and fix incomplete match scores where the final round was missed.
    This happens when VLR.gg removes live data before we can scrape the final round.
    """
    try:
        if 'map_rounds' not in live_data:
            return

        for round_data in live_data['map_rounds']:
            team1_rounds = int(round_data.get('team1_rounds', 0))
            team2_rounds = int(round_data.get('team2_rounds', 0))
            map_name = round_data.get('map_name', 'Unknown')

            # If one team has 12 and the other has less than 11, likely missing final round
            if (team1_rounds == 12 and team2_rounds <= 10) or (team2_rounds == 12 and team1_rounds <= 10):
                logger.info(f"Detected potentially incomplete match {match_id} on {map_name}: {team1_rounds}-{team2_rounds}")

                # Try to determine winner based on which team was closer to 13
                if team1_rounds == 12:
                    corrected_team1 = 13
                    corrected_team2 = team2_rounds
                elif team2_rounds == 12:
                    corrected_team1 = team1_rounds
                    corrected_team2 = 13
                else:
                    continue  # Can't determine winner

                logger.info(f"Attempting to correct score to {corrected_team1}-{corrected_team2}")

                # Update the live_score in database if it exists
                from app.models import LiveScore
                live_score = session.exec(
                    select(LiveScore).where(
                        and_(
                            LiveScore.match_id == match_id,
                            LiveScore.map_name == map_name
                        )
                    )
                ).first()

                if live_score:
                    live_score.team1_rounds = corrected_team1
                    live_score.team2_rounds = corrected_team2
                    session.add(live_score)
                    logger.info(f"Updated LiveScore for match {match_id} on {map_name} to {corrected_team1}-{corrected_team2}")

    except Exception as e:
        logger.error(f"Error in fix_incomplete_match_scores for match {match_id}: {str(e)}")


@celery_app.task(name="app.workers.manual_score_correction")
def manual_score_correction(match_id: int, map_name: str, team1_rounds: int, team2_rounds: int):
    """
    Manually correct the score for a specific match and map.
    Use this to fix matches where the final round was missed.
    """
    try:
        with Session(engine) as session:
            # Update LiveScore
            live_score = session.exec(
                select(LiveScore).where(
                    and_(
                        LiveScore.match_id == match_id,
                        LiveScore.current_map == map_name
                    )
                )
            ).first()

            if live_score:
                old_score = f"{live_score.team1_score}-{live_score.team2_score}"
                live_score.team1_score = team1_rounds
                live_score.team2_score = team2_rounds
                session.add(live_score)

                # Also update MapRound if it exists
                map_round = session.exec(
                    select(MapRound).where(
                        and_(
                            MapRound.match_id == match_id,
                            MapRound.map_name == map_name
                        )
                    )
                ).first()

                if map_round:
                    map_round.team1_rounds = team1_rounds
                    map_round.team2_rounds = team2_rounds
                    session.add(map_round)

                session.commit()
                logger.info(f"Manually corrected match {match_id} on {map_name} from {old_score} to {team1_rounds}-{team2_rounds}")
                return f"Successfully updated match {match_id} on {map_name} to {team1_rounds}-{team2_rounds}"
            else:
                logger.warning(f"No LiveScore found for match {match_id} on {map_name}")
                return f"No data found for match {match_id} on {map_name}"

    except Exception as e:
        logger.error(f"Error in manual_score_correction: {str(e)}")
        return f"Error: {str(e)}"

@celery_app.task(name="app.workers.live_match_scraper", bind=True, max_retries=3, default_retry_delay=30)
def scrape_live_match_data(self, match_id: int):
    logger.info(f"Starting Celery task for match ID: {match_id}")

    try:
        with Session(engine) as session:
            match = session.exec(select(Match).where(Match.id == match_id)).first()
            if not match:
                logger.error(f"Match with ID {match_id} not found in the database.")
                return

            match_page_url = match.match_page
            if not match_page_url:
                logger.error(f"No match page URL found for match ID {match_id}.")
                return

            live_data = asyncio.run(_scrape_live_match_data(match_page_url))
            if not live_data:
                logger.warning(f"No live data scraped for match ID {match_id}.")
                return
            logger.info(f"Live data scraped successfully for match ID {match_id}: {live_data}")
            # Process live score - upsert (update if exists, insert if not)
            if 'live_score' in live_data:
                live_score_data = live_data['live_score']

                # Check if live score already exists for this match
                existing_live_score = session.exec(
                    select(LiveScore).where(LiveScore.match_id == match_id)
                ).first()

                if existing_live_score:
                    # Update existing record
                    existing_live_score.team1_score = live_score_data['team1_score']
                    existing_live_score.team2_score = live_score_data['team2_score']
                    existing_live_score.current_map = live_score_data['current_map']
                    existing_live_score.timestamp = datetime.now(timezone.utc)
                    logger.info(f"Updated existing live score for match {match_id}")
                else:
                    # Create new record
                    live_score = LiveScore(
                        match_id=match_id,
                        team1_score=live_score_data['team1_score'],
                        team2_score=live_score_data['team2_score'],
                        current_map=live_score_data['current_map']
                    )
                    session.add(live_score)
                    logger.info(f"Created new live score for match {match_id}")
            # Process map rounds - upsert (update if exists, insert if not)
            if 'map_rounds' in live_data:
                for round_data in live_data['map_rounds']:
                    map_name = round_data['map_name']

                    # Check if map round already exists for this match and map
                    existing_map_round = session.exec(
                        select(MapRound).where(
                            MapRound.match_id == match_id,
                            MapRound.map_name == map_name
                        )
                    ).first()

                    if existing_map_round:
                        # Update existing record
                        existing_map_round.team1_rounds = round_data['team1_rounds']
                        existing_map_round.team2_rounds = round_data['team2_rounds']
                        existing_map_round.team1_attack_rounds = round_data.get('team1_attack_rounds')
                        existing_map_round.team1_defense_rounds = round_data.get('team1_defense_rounds')
                        existing_map_round.team2_attack_rounds = round_data.get('team2_attack_rounds')
                        existing_map_round.team2_defense_rounds = round_data.get('team2_defense_rounds')
                        # Note: MapRound model doesn't have a timestamp field
                        logger.info(f"Updated existing map round for match {match_id}, map {map_name}")
                    else:
                        # Create new record
                        map_round = MapRound(
                            match_id=match_id,
                            map_name=map_name,
                            team1_rounds=round_data['team1_rounds'],
                            team2_rounds=round_data['team2_rounds'],
                            team1_attack_rounds=round_data.get('team1_attack_rounds'),
                            team1_defense_rounds=round_data.get('team1_defense_rounds'),
                            team2_attack_rounds=round_data.get('team2_attack_rounds'),
                            team2_defense_rounds=round_data.get('team2_defense_rounds')
                        )
                        session.add(map_round)
                        logger.info(f"Created new map round for match {match_id}, map {map_name}")
            # Process player stats - upsert (update if exists, insert if not)
            if 'players' in live_data:
                for player_data in live_data['players']:
                    kills = int(player_data['kills'])
                    assists = int(player_data['assists'])
                    deaths = int(player_data.get('deaths', 0))
                    # Calculate score: 1 point per kill + 0.25 points per assist
                    score = kills * 1.0 + assists * 0.25

                    player_name = player_data['player_name']
                    map_name = player_data.get('map_name')
                    agent = player_data.get('agent')

                    # Check if player stat already exists for this match, player, and map
                    existing_player_stat = session.exec(
                        select(PlayerStat).where(
                            PlayerStat.match_id == match_id,
                            PlayerStat.player_name == player_name,
                            PlayerStat.map_name == map_name
                        )
                    ).first()

                    if existing_player_stat:
                        # Update existing record
                        existing_player_stat.agent = agent
                        existing_player_stat.kills = kills
                        existing_player_stat.deaths = deaths
                        existing_player_stat.assists = assists
                        existing_player_stat.score = score
                        logger.info(f"Updated player stat for {player_name} on {map_name} in match {match_id}")
                    else:
                        # Create new record
                        player_stat = PlayerStat(
                            match_id=match_id,
                            map_name=map_name,
                            player_name=player_name,
                            agent=agent,
                            kills=kills,
                            deaths=deaths,
                            assists=assists,
                            score=score
                        )
                        session.add(player_stat)
                        logger.info(f"Created new player stat for {player_name} on {map_name} in match {match_id}")

            # Check if match is close to ending and schedule rapid updates
            if 'map_rounds' in live_data:
                for round_data in live_data['map_rounds']:
                    team1_rounds = int(round_data.get('team1_rounds', 0))
                    team2_rounds = int(round_data.get('team2_rounds', 0))

                    # If either team has 12 rounds, match is close to ending
                    if team1_rounds >= 12 or team2_rounds >= 12:
                        logger.info(f"Match {match_id} is close to ending ({team1_rounds}-{team2_rounds}). Scheduling rapid updates.")
                        # Schedule additional scrapes in 15, 30, 45 seconds
                        from app.celery_app import celery_app
                        celery_app.send_task('app.workers.live_match_scraper', args=[match_id], countdown=15)
                        celery_app.send_task('app.workers.live_match_scraper', args=[match_id], countdown=30)
                        celery_app.send_task('app.workers.live_match_scraper', args=[match_id], countdown=45)
                        break

            session.commit()

            # Check for incomplete matches and attempt to fix them
            fix_incomplete_match_scores(session, match_id, live_data)

            # Log summary of what was processed
            total_live_scores = len(live_data.get('live_score', []))
            total_map_rounds = len(live_data.get('map_rounds', []))
            total_players = len(live_data.get('players', []))

            logger.info(f"Live match data for match ID {match_id} processed successfully:")
            logger.info(f"  - Live scores: {total_live_scores}")
            logger.info(f"  - Map rounds: {total_map_rounds}")
            logger.info(f"  - Player stats: {total_players}")
            logger.info(f"All data has been upserted (updated existing or created new records) in the database.")

            # Optionally run cleanup to remove any remaining duplicates
            # This is useful for the first few runs after implementing upsert logic
            # cleanup_duplicate_live_data.delay(match_id)
    except Exception as exc:
        logger.error(f"Error in scrape_live_match_data_task for match ID {match_id}: {str(exc)}", exc_info=True)
        # Retry the task if it fails
        self.retry(exc=exc, countdown=self.default_retry_delay)


@celery_app.task(bind=True, name="cleanup_duplicate_live_data")
def cleanup_duplicate_live_data(self, match_id: int):
    """
    Clean up duplicate live data entries for a specific match.
    Keeps only the most recent entry for each unique combination.
    """
    logger.info(f"Starting cleanup of duplicate live data for match ID: {match_id}")

    try:
        with Session(engine) as session:
            # Clean up duplicate LiveScore entries - keep only the most recent
            duplicate_live_scores = session.exec(
                select(LiveScore)
                .where(LiveScore.match_id == match_id)
                .order_by(LiveScore.timestamp.desc())
            ).all()

            if len(duplicate_live_scores) > 1:
                # Keep the first (most recent) and delete the rest
                for live_score in duplicate_live_scores[1:]:
                    session.delete(live_score)
                logger.info(f"Removed {len(duplicate_live_scores) - 1} duplicate live score entries for match {match_id}")

            # Clean up duplicate PlayerStat entries - keep only the most recent for each player+map combination
            # Get all unique player+map combinations for this match
            unique_combinations = session.exec(
                select(PlayerStat.player_name, PlayerStat.map_name)
                .where(PlayerStat.match_id == match_id)
                .distinct()
            ).all()

            total_removed_player_stats = 0
            for player_name, map_name in unique_combinations:
                duplicate_player_stats = session.exec(
                    select(PlayerStat)
                    .where(
                        PlayerStat.match_id == match_id,
                        PlayerStat.player_name == player_name,
                        PlayerStat.map_name == map_name
                    )
                    .order_by(PlayerStat.id.desc())  # Most recent first (assuming higher ID = more recent)
                ).all()

                if len(duplicate_player_stats) > 1:
                    # Keep the first (most recent) and delete the rest
                    for player_stat in duplicate_player_stats[1:]:
                        session.delete(player_stat)
                    total_removed_player_stats += len(duplicate_player_stats) - 1

            if total_removed_player_stats > 0:
                logger.info(f"Removed {total_removed_player_stats} duplicate player stat entries for match {match_id}")

            # Clean up duplicate MapRound entries - keep only the most recent for each map
            unique_maps = session.exec(
                select(MapRound.map_name)
                .where(MapRound.match_id == match_id)
                .distinct()
            ).all()

            total_removed_map_rounds = 0
            for map_name in unique_maps:
                duplicate_map_rounds = session.exec(
                    select(MapRound)
                    .where(
                        MapRound.match_id == match_id,
                        MapRound.map_name == map_name
                    )
                    .order_by(MapRound.id.desc())  # Use id instead of timestamp since MapRound doesn't have timestamp
                ).all()

                if len(duplicate_map_rounds) > 1:
                    # Keep the first (most recent) and delete the rest
                    for map_round in duplicate_map_rounds[1:]:
                        session.delete(map_round)
                    total_removed_map_rounds += len(duplicate_map_rounds) - 1

            if total_removed_map_rounds > 0:
                logger.info(f"Removed {total_removed_map_rounds} duplicate map round entries for match {match_id}")

            session.commit()
            logger.info(f"Cleanup completed for match ID {match_id}")

    except Exception as exc:
        logger.error(f"Error in cleanup_duplicate_live_data for match ID {match_id}: {str(exc)}", exc_info=True)
        self.retry(exc=exc, countdown=60)  # Retry after 1 minute

