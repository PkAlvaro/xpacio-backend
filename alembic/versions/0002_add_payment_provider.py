"""add payment provider column

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE payment_provider AS ENUM ('stripe', 'transbank')")
    op.add_column(
        "payments",
        sa.Column(
            "provider",
            sa.Enum("stripe", "transbank", name="payment_provider"),
            nullable=False,
            server_default="stripe",
        ),
    )
    op.alter_column("payments", "provider", server_default=None)


def downgrade() -> None:
    op.drop_column("payments", "provider")
    op.execute("DROP TYPE payment_provider")
