"""add per-account institution logo url

Revision ID: 075
Revises: 074
Create Date: 2026-08-25

Akahu aggregates many institutions under a single connection (e.g. ASB,
Hatch, Gem Visa), but only the connection-level logo was stored, so every
account rendered the first institution's logo. Add an optional per-account
logo URL so each account can show its own bank's logo.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "075"
down_revision: Union[str, None] = "074"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "logo_url")
