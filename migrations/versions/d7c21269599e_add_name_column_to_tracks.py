"""add_name_column_to_tracks

Revision ID: d7c21269599e
Revises: 
Create Date: 2025-06-03 21:39:56.470148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7c21269599e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tracks', sa.Column('name', sa.String(), nullable=True))
    
    # Create unique index on name column
    op.create_index(op.f('ix_tracks_name'), 'tracks', ['name'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tracks_name'), table_name='tracks')
    op.drop_column('tracks', 'name')
