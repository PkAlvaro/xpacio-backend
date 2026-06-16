"""add slug to spaces

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("spaces", sa.Column("slug", sa.String(300), nullable=True))
    op.create_index("ix_spaces_slug", "spaces", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_spaces_slug", table_name="spaces")
    op.drop_column("spaces", "slug")
