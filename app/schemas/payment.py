import uuid
from pydantic import BaseModel
from app.constants import PaymentStatus, PaymentProvider


class PaymentInitiateStripe(BaseModel):
    reservation_id: uuid.UUID

    model_config = {
        "json_schema_extra": {
            "example": {"reservation_id": "00000000-0000-0000-0000-000000000000"}
        }
    }


class PaymentInitiateTransbank(BaseModel):
    reservation_id: uuid.UUID

    model_config = {
        "json_schema_extra": {
            "example": {"reservation_id": "00000000-0000-0000-0000-000000000000"}
        }
    }


# Mantener para compatibilidad interna
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
