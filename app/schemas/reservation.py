import uuid
from datetime import date, time
from typing import Annotated
from pydantic import BaseModel, Field, model_validator
from app.constants import ReservationStatus


class ReservationCreate(BaseModel):
    space_id: uuid.UUID
    date: date
    start_time: time
    end_time: time
    num_people: Annotated[int, Field(ge=1)] = 1  # SC-001 — para descuento por volumen

    @model_validator(mode="after")
    def validate_times(self) -> "ReservationCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time debe ser posterior a start_time")
        return self


class ReservationResponse(BaseModel):
    id: uuid.UUID
    space_id: uuid.UUID
    space_name: str | None = None
    client_id: uuid.UUID
    date: date
    start_time: time
    end_time: time
    hours: int
    num_people: int = 1
    subtotal: int
    service_fee: int
    total: int
    status: ReservationStatus
    model_config = {"from_attributes": True}


class IncomingReservationResponse(ReservationResponse):
    space_name: str | None = None
    client_name: str | None = None
    client_email: str | None = None


class ReservationCancel(BaseModel):
    reason: str | None = None
