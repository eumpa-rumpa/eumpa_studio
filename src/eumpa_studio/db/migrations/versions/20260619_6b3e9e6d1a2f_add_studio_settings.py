"""add studio settings

Revision ID: 6b3e9e6d1a2f
Revises: 21294ea57d30
Create Date: 2026-06-19 00:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b3e9e6d1a2f"
down_revision: Union[str, Sequence[str], None] = "21294ea57d30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the migration."""
    op.create_table(
        "studio_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    """Revert the migration."""
    op.drop_table("studio_settings")
