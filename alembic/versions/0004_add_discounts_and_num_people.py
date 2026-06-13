"""SC-001: discounts on spaces + num_people on reservations

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SC-001 — enum de tipo de descuento
    op.execute("CREATE TYPE discount_type AS ENUM ('percentage', 'volume')")

    op.add_column(
        "spaces",
        sa.Column("discount_type", sa.Enum("percentage", "volume", name="discount_type"), nullable=True),
    )
    op.add_column("spaces", sa.Column("discount_value", sa.Numeric(5, 2), nullable=True))
    op.add_column(
        "spaces",
        sa.Column("discount_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("spaces", sa.Column("discount_min_people", sa.Integer(), nullable=True))
    op.alter_column("spaces", "discount_active", server_default=None)
    op.create_index("ix_spaces_discount_active", "spaces", ["discount_active"])

    # SC-001 — num_people para descuentos por volumen
    op.add_column(
        "reservations",
        sa.Column("num_people", sa.Integer(), nullable=False, server_default="1"),
    )
    op.alter_column("reservations", "num_people", server_default=None)


def downgrade() -> None:
    op.drop_column("reservations", "num_people")
    op.drop_index("ix_spaces_discount_active", table_name="spaces")
    op.drop_column("spaces", "discount_min_people")
    op.drop_column("spaces", "discount_active")
    op.drop_column("spaces", "discount_value")
    op.drop_column("spaces", "discount_type")
    op.execute("DROP TYPE discount_type")
