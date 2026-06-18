"""allow one dispute per party per reservation

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-18
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("disputes_reservation_id_key", "disputes", type_="unique")
    op.create_unique_constraint(
        "uq_disputes_reservation_opened_by",
        "disputes",
        ["reservation_id", "opened_by"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_disputes_reservation_opened_by", "disputes", type_="unique")
    op.create_unique_constraint("disputes_reservation_id_key", "disputes", ["reservation_id"])
