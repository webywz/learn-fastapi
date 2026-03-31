"""Add visibility to files

Revision ID: 91e4a2b7f6b0
Revises: 6f3c5d4c8b21
Create Date: 2026-03-31 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "91e4a2b7f6b0"
down_revision: Union[str, Sequence[str], None] = "6f3c5d4c8b21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column(
            "visibility",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'private'"),
            comment="可见性（private/public）",
        ),
    )


def downgrade() -> None:
    op.drop_column("files", "visibility")
