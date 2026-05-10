import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, Enum as SAEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, new_uuid
from app.constants import VerificationStatus


class Provider(Base, TimestampMixin):
    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    bank_rut: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status", values_callable=lambda x: [e.value for e in x]),
        default=VerificationStatus.PENDING,
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="provider")
    spaces = relationship("Space", back_populates="provider")
