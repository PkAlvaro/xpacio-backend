import uuid
from pydantic import BaseModel
from app.constants import VerificationStatus


class ProviderResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    bio: str | None
    bank_rut: str | None
    bank_account: str | None
    verification_status: VerificationStatus

    model_config = {"from_attributes": True}


class ProviderUpdate(BaseModel):
    bio: str | None = None
    bank_rut: str | None = None
    bank_account: str | None = None
