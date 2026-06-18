import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator
from app.constants import DisputeStatus


class DisputeOpen(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 20:
            raise ValueError("El motivo debe tener al menos 20 caracteres")
        return v


class DisputeResolve(BaseModel):
    decision: str  # "refund" | "reject"
    admin_notes: str | None = None
    refund_amount: int | None = None

    @field_validator("decision")
    @classmethod
    def valid_decision(cls, v: str) -> str:
        if v not in ("refund", "reject"):
            raise ValueError("decision debe ser 'refund' o 'reject'")
        return v


class DisputeEvidenceOut(BaseModel):
    id: uuid.UUID
    url: str
    filename: str | None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DisputeResponse(BaseModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    opened_by: uuid.UUID
    opener_name: str | None = None
    opener_email: str | None = None
    space_name: str | None = None
    reason: str
    status: DisputeStatus
    admin_notes: str | None
    refund_amount: int | None
    resolved_at: datetime | None
    resolved_by: uuid.UUID | None
    evidence: list[DisputeEvidenceOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}
