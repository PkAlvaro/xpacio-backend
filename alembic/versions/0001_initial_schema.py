"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("client", "provider", "admin", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bank_rut", sa.String(20), nullable=True),
        sa.Column("bank_account", sa.String(50), nullable=True),
        sa.Column("bio", sa.String(500), nullable=True),
        sa.Column("verification_status", sa.Enum("pending", "verified", "rejected", name="verification_status"), nullable=False, server_default="pending"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.Enum("Oficina", "Cancha", "Sala", "Salón", "Estudio", "Terraza", name="space_type"), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=True),
        sa.Column("lng", sa.Numeric(9, 6), nullable=True),
        sa.Column("price_per_hour", sa.Integer, nullable=False),
        sa.Column("capacity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("cancellation_policy", sa.Enum("flexible", "moderate", "strict", name="cancellation_policy"), nullable=False, server_default="flexible"),
        sa.Column("cancellation_hours", sa.Integer, nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("rating", sa.Numeric(3, 2), nullable=False, server_default="0.0"),
        sa.Column("review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_spaces_provider_id", "spaces", ["provider_id"])
    op.create_index("ix_spaces_city", "spaces", ["city"])
    op.create_index("ix_spaces_type", "spaces", ["type"])

    op.create_table(
        "space_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer, nullable=False),
        sa.Column("open_time", sa.String(5), nullable=False),
        sa.Column("close_time", sa.String(5), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("space_id", "day_of_week", name="uq_space_schedule_day"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_schedule_day_range"),
    )

    op.create_table(
        "space_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "space_amenities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("hours", sa.Integer, nullable=False),
        sa.Column("subtotal", sa.Integer, nullable=False),
        sa.Column("service_fee", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total", sa.Integer, nullable=False),
        sa.Column("status", sa.Enum("pending", "confirmed", "active", "finished", "cancelled", "expired", name="reservation_status"), nullable=False, server_default="pending"),
        sa.Column("cancellation_reason", sa.Text, nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"]),
        sa.CheckConstraint("end_time > start_time", name="ck_reservation_time_order"),
    )
    op.create_index("ix_reservations_space_id", "reservations", ["space_id"])
    op.create_index("ix_reservations_client_id", "reservations", ["client_id"])
    op.create_index("ix_reservations_status", "reservations", ["status"])
    op.create_index("ix_reservations_date", "reservations", ["date"])

    # Exclusion constraint — prevents overlapping reservations for same space+date
    # Requires btree_gist extension (created above)
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

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("buy_order", sa.String(26), nullable=False),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("status", sa.Enum("initiated", "paid", "failed", "refunded", name="payment_status"), nullable=False, server_default="initiated"),
        sa.Column("raw_response", postgresql.JSONB, nullable=True),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id"),
        sa.UniqueConstraint("token"),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"]),
    )
    op.create_index("ix_payments_token", "payments", ["token"])

    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id"),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"]),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
    )

    op.create_table(
        "favorites",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "space_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_table("reviews")
    op.drop_table("payments")
    op.drop_table("reservations")
    op.drop_table("space_amenities")
    op.drop_table("space_images")
    op.drop_table("space_schedules")
    op.drop_table("spaces")
    op.drop_table("providers")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS payment_status")
    op.execute("DROP TYPE IF EXISTS reservation_status")
    op.execute("DROP TYPE IF EXISTS cancellation_policy")
    op.execute("DROP TYPE IF EXISTS space_type")
    op.execute("DROP TYPE IF EXISTS verification_status")
    op.execute("DROP TYPE IF EXISTS user_role")
