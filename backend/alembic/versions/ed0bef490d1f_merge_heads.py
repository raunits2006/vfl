"""merge heads

Revision ID: ed0bef490d1f
Revises: adc01234abcd, d2d2c3a1e5f0
Create Date: 2025-08-16 21:57:56.845129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ed0bef490d1f'
down_revision: Union[str, None] = ('adc01234abcd', 'd2d2c3a1e5f0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
