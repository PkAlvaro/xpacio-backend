import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin, new_uuid
from app.constants import PaymentStatus


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    reservation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reservations.id"), unique=True, nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    buy_order: Mapped[str] = mapped_column(String(26), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", values_callable=lambda x: [e.value for e in x]),
        default=PaymentStatus.INITIATED,
        nullable=False,
    )
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reservation = relationship("Reservation", back_populates="payment")
