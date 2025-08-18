"""add agent prediction table

Revision ID: d2d2c3a1e5f0
Revises: cebc5bac8311
Create Date: 2025-08-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2d2c3a1e5f0'
down_revision = 'c1f2e3d4a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'agentprediction',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('team.id', ondelete='CASCADE'), nullable=False),
        sa.Column('player_name', sa.String(), sa.ForeignKey('players.player_name', ondelete='CASCADE'), nullable=False),
        sa.Column('picks_csv', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_agentprediction_team_player_created', 'agentprediction', ['team_id', 'player_name', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_agentprediction_team_player_created', table_name='agentprediction')
    op.drop_table('agentprediction')


