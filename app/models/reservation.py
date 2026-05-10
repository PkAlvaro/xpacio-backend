import uuid
from datetime import datetime, date, time
from sqlalchemy import String, Integer, Date, Time, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, new_uuid
from app.constants import ReservationStatus


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id"), nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    hours: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[int] = mapped_column(Integer, nullable=False)
    service_fee: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus, name="reservation_status", values_callable=lambda x: [e.value for e in x]),
        default=ReservationStatus.PENDING,
        nullable=False,
        index=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    space = relationship("Space", back_populates="reservations")
    client = relationship("User", back_populates="reservations", foreign_keys=[client_id])
    payment = relationship("Payment", back_populates="reservation", uselist=False)
    review = relationship("Review", back_populates="reservation", uselist=False)


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    reservation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reservations.id"), unique=True, nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    reservation = relationship("Reservation", back_populates="review")
    client = relationship("User", back_populates="reviews")
    space = relationship("Space", back_populates="reviews")


class Favorite(Base):
    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id"), primary_key=True)
