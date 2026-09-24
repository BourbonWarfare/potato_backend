"""add arma events

Revision ID: b6f0e3d8c7a1
Revises: 7498f41deef6
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b6f0e3d8c7a1'
down_revision: Union[str, Sequence[str], None] = '2c4a6b8d9e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'arma_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('creation_date', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('tag', sa.String(length=128), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_arma_events_creation_date'), 'arma_events', ['creation_date'], unique=False)
    op.create_index(op.f('ix_arma_events_tag'), 'arma_events', ['tag'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_arma_events_tag'), table_name='arma_events')
    op.drop_index(op.f('ix_arma_events_creation_date'), table_name='arma_events')
    op.drop_table('arma_events')
