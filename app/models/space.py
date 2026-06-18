import uuid
from sqlalchemy import String, Integer, Boolean, Numeric, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, new_uuid
from app.constants import SpaceType, CancellationPolicy, DiscountType


class Space(Base, TimestampMixin):
    __tablename__ = "spaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=False, index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(300), nullable=True, unique=True, index=True)
    type: Mapped[SpaceType] = mapped_column(SAEnum(SpaceType, name="space_type", values_callable=lambda x: [e.value for e in x]), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    price_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cancellation_policy: Mapped[CancellationPolicy] = mapped_column(
        SAEnum(CancellationPolicy, name="cancellation_policy", values_callable=lambda x: [e.value for e in x]),
        default=CancellationPolicy.FLEXIBLE,
        nullable=False,
    )
    cancellation_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # SC-001 — Descuentos / Ofertas (REQ-2.3 / REQ-3.5)
    # Se almacenan de forma independiente para no corromper el precio base histórico.
    discount_type: Mapped[DiscountType | None] = mapped_column(
        SAEnum(DiscountType, name="discount_type", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    discount_value: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # % de descuento
    discount_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    discount_min_people: Mapped[int | None] = mapped_column(Integer, nullable=True)  # mínimo para descuento por volumen

    provider = relationship("Provider", back_populates="spaces")
    schedules = relationship("SpaceSchedule", back_populates="space", cascade="all, delete-orphan")
    images = relationship("SpaceImage", back_populates="space", cascade="all, delete-orphan", order_by="SpaceImage.display_order")
    amenities = relationship("SpaceAmenity", back_populates="space", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="space")
    reviews = relationship("Review", back_populates="space")
    sub_spaces = relationship("Space", back_populates="parent", cascade="all, delete-orphan", foreign_keys="Space.parent_id")
    parent = relationship("Space", back_populates="sub_spaces", remote_side="Space.id", foreign_keys="Space.parent_id")


class SpaceSchedule(Base):
    __tablename__ = "space_schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon, 6=Sun
    open_time: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM"
    close_time: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM"

    space = relationship("Space", back_populates="schedules")


class SpaceImage(Base):
    __tablename__ = "space_images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    space = relationship("Space", back_populates="images")


class SpaceAmenity(Base):
    __tablename__ = "space_amenities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    space = relationship("Space", back_populates="amenities")
