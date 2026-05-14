"""add google_event_id to reservations

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reservations", sa.Column("google_event_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("reservations", "google_event_id")
