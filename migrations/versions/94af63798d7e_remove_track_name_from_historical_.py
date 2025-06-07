"""Remove track_name from historical_performances

Revision ID: 94af63798d7e
Revises: 
Create Date: 2025-06-05 19:07:36.275299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94af63798d7e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop track_name column from historical_performances table
    op.drop_column('historical_performances', 'track_name')


def downgrade() -> None:
    """Downgrade schema."""
    # Add track_name column back to historical_performances table
    op.add_column('historical_performances', sa.Column('track_name', sa.String(), nullable=True))
