"""add audit_logs, user_notes, space approval_status

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("detail", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )

    op.create_table(
        "user_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("admin_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )

    op.execute("CREATE TYPE space_approval_status AS ENUM ('pending', 'approved', 'rejected')")
    op.add_column("spaces", sa.Column(
        "approval_status",
        sa.Enum("pending", "approved", "rejected", name="space_approval_status"),
        nullable=False,
        server_default="approved",
    ))
    op.add_column("spaces", sa.Column("approval_note", sa.Text(), nullable=True))
    op.create_index("ix_spaces_approval_status", "spaces", ["approval_status"])


def downgrade() -> None:
    op.drop_index("ix_spaces_approval_status", "spaces")
    op.drop_column("spaces", "approval_note")
    op.drop_column("spaces", "approval_status")
    op.execute("DROP TYPE space_approval_status")
    op.drop_table("user_notes")
    op.drop_table("audit_logs")
