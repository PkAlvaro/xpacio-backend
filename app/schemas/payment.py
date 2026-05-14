import uuid
from pydantic import BaseModel
from app.constants import PaymentStatus, PaymentProvider


class PaymentInitiate(BaseModel):
    reservation_id: uuid.UUID
    provider: PaymentProvider


class PaymentInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    provider: PaymentProvider
    redirect_url: str
    token: str


class PaymentResponse(BaseModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    provider: PaymentProvider
    amount: int
    status: PaymentStatus
    authorized_at: str | None = None
    model_config = {"from_attributes": True}
