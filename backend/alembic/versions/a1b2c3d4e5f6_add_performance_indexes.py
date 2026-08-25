"""add performance indexes

Revision ID: a1b2c3d4e5f6
Revises: ed0bef490d1f
Create Date: 2025-08-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ed0bef490d1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Match: status filter is common in live-match discovery queries
    op.create_index('ix_match_status', 'match', ['status'])

    # Match: unix_timestamp range scans for time-based lookups
    op.create_index('ix_match_unix_timestamp', 'match', ['unix_timestamp'])

    # Match: compound index for the most common live-match query pattern
    op.create_index(
        'ix_match_status_timestamp',
        'match',
        ['status', 'unix_timestamp'],
    )

    # PlayerStat: frequently joined with Match on match_id
    op.create_index('ix_playerstat_match_id', 'playerstat', ['match_id'])

    # PlayerStat: queried by player_name for fantasy score calculation
    op.create_index('ix_playerstat_player_name', 'playerstat', ['player_name'])

    # PlayerStat: compound index for the primary scoring query path
    op.create_index(
        'ix_playerstat_match_player_map',
        'playerstat',
        ['match_id', 'player_name', 'map_name'],
    )

    # TeamPlayer: frequent lookups by team_id
    op.create_index('ix_teamplayer_team_id', 'teamplayer', ['team_id'])

    # DraftPick: queried by draft_session_id ordered by pick_number
    op.create_index(
        'ix_draftpick_session_pick',
        'draftpick',
        ['draft_session_id', 'pick_number'],
    )

    # FreeAgentTransaction: queried by league_id for activity feeds
    op.create_index(
        'ix_freeagenttransaction_league_date',
        'freeagenttransaction',
        ['league_id', 'transaction_date'],
    )

    # LeagueMember: compound index for league+user lookup
    op.create_index(
        'ix_leaguemember_league_user',
        'leaguemember',
        ['league_id', 'user_id'],
    )

    # Trade: league-scoped trade queries
    op.create_index('ix_trade_league_status', 'trade', ['league_id', 'status'])


def downgrade() -> None:
    op.drop_index('ix_trade_league_status', table_name='trade')
    op.drop_index('ix_leaguemember_league_user', table_name='leaguemember')
    op.drop_index('ix_freeagenttransaction_league_date', table_name='freeagenttransaction')
    op.drop_index('ix_draftpick_session_pick', table_name='draftpick')
    op.drop_index('ix_teamplayer_team_id', table_name='teamplayer')
    op.drop_index('ix_playerstat_match_player_map', table_name='playerstat')
    op.drop_index('ix_playerstat_player_name', table_name='playerstat')
    op.drop_index('ix_playerstat_match_id', table_name='playerstat')
    op.drop_index('ix_match_status_timestamp', table_name='match')
    op.drop_index('ix_match_unix_timestamp', table_name='match')
    op.drop_index('ix_match_status', table_name='match')