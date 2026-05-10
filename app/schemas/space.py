import uuid
from typing import Annotated
from pydantic import BaseModel, Field, field_validator
from app.constants import SpaceType, CancellationPolicy


class SpaceImageOut(BaseModel):
    id: uuid.UUID
    url: str
    is_primary: bool
    display_order: int
    model_config = {"from_attributes": True}


class SpaceScheduleOut(BaseModel):
    id: uuid.UUID
    day_of_week: int
    open_time: str
    close_time: str
    model_config = {"from_attributes": True}


class SpaceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    type: SpaceType
    description: str | None = None
    address: str = Field(min_length=5)
    city: str = Field(min_length=2)
    price_per_hour: Annotated[int, Field(gt=0)]
    capacity: Annotated[int, Field(gt=0)] = 1
    cancellation_policy: CancellationPolicy = CancellationPolicy.FLEXIBLE
    cancellation_hours: Annotated[int, Field(ge=0)] = 24
    amenities: list[str] = []


class SpaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3)
    description: str | None = None
    price_per_hour: Annotated[int | None, Field(default=None, gt=0)] = None
    capacity: Annotated[int | None, Field(default=None, gt=0)] = None
    cancellation_policy: CancellationPolicy | None = None
    cancellation_hours: Annotated[int | None, Field(default=None, ge=0)] = None
    is_active: bool | None = None
    amenities: list[str] | None = None


class SpaceResponse(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    name: str
    type: SpaceType
    description: str | None
    address: str
    city: str
    lat: float | None
    lng: float | None
    price_per_hour: int
    capacity: int
    cancellation_policy: CancellationPolicy
    cancellation_hours: int
    is_active: bool
    rating: float
    review_count: int
    images: list[SpaceImageOut] = []
    schedules: list[SpaceScheduleOut] = []
    amenities: list[str] = []
    model_config = {"from_attributes": True}

    @field_validator("amenities", mode="before")
    @classmethod
    def coerce_amenities(cls, v):
        if v and hasattr(v[0], "name"):
            return [a.name for a in v]
        return v

    @classmethod
    def from_orm_with_amenities(cls, space) -> "SpaceResponse":
        return cls.model_validate(space)


class SpaceListItem(BaseModel):
    id: uuid.UUID
    name: str
    type: SpaceType
    city: str
    address: str
    lat: float | None
    lng: float | None
    price_per_hour: int
    capacity: int
    rating: float
    review_count: int
    is_active: bool
    primary_image: str | None = None
    distance_km: float | None = None
    model_config = {"from_attributes": True}


class SpaceFilters(BaseModel):
    lat: float | None = None
    lng: float | None = None
    radius_km: float = Field(default=10.0, gt=0)
    type: SpaceType | None = None
    city: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=50)] = 20


class ScheduleCreate(BaseModel):
    day_of_week: Annotated[int, Field(ge=0, le=6)]
    open_time: str
    close_time: str

    @field_validator("open_time", "close_time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Formato de hora inválido. Use HH:MM")
        h, m = parts
        if not (h.isdigit() and m.isdigit()):
            raise ValueError("Formato de hora inválido. Use HH:MM")
        if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            raise ValueError("Hora fuera de rango")
        return v
