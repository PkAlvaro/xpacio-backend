"""Agregar parent_id a spaces para sub-espacios/salas

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-15
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "spaces",
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("spaces.id", ondelete="CASCADE"), nullable=True),
    )
    op.create_index("ix_spaces_parent_id", "spaces", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_spaces_parent_id", table_name="spaces")
    op.drop_column("spaces", "parent_id")
