import uuid
from pydantic import BaseModel
from app.constants import PaymentStatus


class PaymentInitiate(BaseModel):
    reservation_id: uuid.UUID


class PaymentInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    webpay_url: str
    token: str


class PaymentResponse(BaseModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    amount: int
    status: PaymentStatus
    authorized_at: str | None = None
    model_config = {"from_attributes": True}
