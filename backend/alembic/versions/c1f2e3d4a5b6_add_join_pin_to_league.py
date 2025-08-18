"""add join_pin to league

Revision ID: c1f2e3d4a5b6
Revises: 9878a26aa20b
Create Date: 2025-08-08 06:45:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1f2e3d4a5b6'
down_revision: Union[str, None] = '9878a26aa20b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('league', schema=None) as batch_op:
        batch_op.add_column(sa.Column('join_pin', sa.String(length=6), nullable=True))
        batch_op.create_index('ix_league_join_pin', ['join_pin'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('league', schema=None) as batch_op:
        batch_op.drop_index('ix_league_join_pin')
        batch_op.drop_column('join_pin')


