"""add_max_duelist_agent_players_to_league_settings

Revision ID: f1a2b3c4d5e6
Revises: e98d52dd1f39
Create Date: 2026-01-09 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e98d52dd1f39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('leaguesettings', sa.Column('max_duelist_agent_players', sa.Integer(), nullable=False, server_default=sa.text('2')))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('leaguesettings', 'max_duelist_agent_players')
