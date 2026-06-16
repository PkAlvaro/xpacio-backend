"""add end_date to reservations, drop single-day exclusion constraint

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop constraint — only handled same-day overlaps; replaced by service-level check
    op.execute("ALTER TABLE reservations DROP CONSTRAINT IF EXISTS excl_no_overlap")

    op.add_column("reservations", sa.Column("end_date", sa.Date(), nullable=True))

    # Backfill: existing reservations end on the same day they start
    op.execute("UPDATE reservations SET end_date = date WHERE end_date IS NULL")


def downgrade() -> None:
    op.drop_column("reservations", "end_date")

    op.execute("""
        ALTER TABLE reservations
        ADD CONSTRAINT excl_no_overlap
        EXCLUDE USING gist (
            space_id WITH =,
            date WITH =,
            int4range(
                extract(hour from start_time)::int * 60 + extract(minute from start_time)::int,
                extract(hour from end_time)::int * 60 + extract(minute from end_time)::int
            ) WITH &&
        )
        WHERE (status NOT IN ('cancelled', 'expired'))
    """)
