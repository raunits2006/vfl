"""add agent prediction multipliers to LeagueSettings

Revision ID: adc01234abcd
Revises: 94132139b3a0
Create Date: 2025-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adc01234abcd'
down_revision: Union[str, None] = '94132139b3a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leaguesettings', sa.Column('agent_exact_match_multiplier', sa.Float(), nullable=False, server_default=sa.text('1.0')))
    op.add_column('leaguesettings', sa.Column('agent_class_match_multiplier', sa.Float(), nullable=False, server_default=sa.text('0.5')))
    op.add_column('leaguesettings', sa.Column('agent_miss_multiplier', sa.Float(), nullable=False, server_default=sa.text('0.25')))


def downgrade() -> None:
    op.drop_column('leaguesettings', 'agent_miss_multiplier')
    op.drop_column('leaguesettings', 'agent_class_match_multiplier')
    op.drop_column('leaguesettings', 'agent_exact_match_multiplier')


