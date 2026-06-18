"""add disputes and dispute_evidence tables

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE IF NOT EXISTS dispute_status AS ENUM (
            'open', 'under_review', 'resolved_refund', 'resolved_rejected'
        )
    """)

    op.create_table(
        "disputes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("reservation_id", UUID(as_uuid=True), sa.ForeignKey("reservations.id"), nullable=False, unique=True),
        sa.Column("opened_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("open", "under_review", "resolved_refund", "resolved_rejected", name="dispute_status", create_type=False), nullable=False, server_default="open"),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("refund_amount", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_disputes_reservation_id", "disputes", ["reservation_id"])
    op.create_index("ix_disputes_status", "disputes", ["status"])

    op.create_table(
        "dispute_evidence",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("dispute_id", UUID(as_uuid=True), sa.ForeignKey("disputes.id"), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dispute_evidence_dispute_id", "dispute_evidence", ["dispute_id"])


def downgrade() -> None:
    op.drop_table("dispute_evidence")
    op.drop_table("disputes")
    op.execute("DROP TYPE IF EXISTS dispute_status")
