import uuid
from sqlalchemy import Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, new_uuid


class SystemConfig(Base, TimestampMixin):
    """Singleton row — always id = fixed UUID. Use get_config() to access."""

    __tablename__ = "system_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    platform_fee_percent: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    dispute_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    pending_reservation_ttl_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    maintenance_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
