import uuid
from datetime import date, time, datetime
from typing import Annotated
from pydantic import BaseModel, Field, model_validator
from app.constants import ReservationStatus


class ReservationCreate(BaseModel):
    space_id: uuid.UUID
    date: date
    end_date: date | None = None
    start_time: time
    end_time: time
    num_people: Annotated[int, Field(ge=1)] = 1

    @model_validator(mode="after")
    def validate_times(self) -> "ReservationCreate":
        effective_end = self.end_date or self.date
        if effective_end < self.date:
            raise ValueError("end_date no puede ser anterior a date")
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(effective_end, self.end_time)
        if end_dt <= start_dt:
            raise ValueError("El fin debe ser posterior al inicio")
        return self


class ReservationResponse(BaseModel):
    id: uuid.UUID
    space_id: uuid.UUID
    space_name: str | None = None
    client_id: uuid.UUID
    date: date
    end_date: date | None = None
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
