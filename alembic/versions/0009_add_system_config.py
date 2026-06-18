"""add system_config singleton table

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-18
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

SINGLETON_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "system_config",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform_fee_percent", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("dispute_window_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("pending_reservation_ttl_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("maintenance_mode", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        f"INSERT INTO system_config (id) VALUES ('{SINGLETON_ID}')"
    )


def downgrade() -> None:
    op.drop_table("system_config")
