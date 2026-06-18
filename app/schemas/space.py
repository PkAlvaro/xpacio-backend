import re
import uuid
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field, field_validator, model_validator
from app.constants import SpaceType, CancellationPolicy, DiscountType

_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
_SQL_RE = re.compile(r"(--|;|/\*|\*/|xp_|UNION\b|SELECT\b|INSERT\b|UPDATE\b|DELETE\b|DROP\b|EXEC\b)", re.IGNORECASE)


def _sanitize(v: str | None, max_len: int = 2000) -> str | None:
    if v is None:
        return v
    v = _CTRL_RE.sub("", v).strip()
    if _SQL_RE.search(v):
        raise ValueError("Entrada no válida")
    return v[:max_len]


def compute_discounted_price(
    price_per_hour: int,
    discount_active: bool,
    discount_type: DiscountType | None,
    discount_value: float | None,
) -> int | None:
    """Precio por hora ya con descuento aplicado, para mostrar en UI.
    Para descuento por volumen el precio efectivo depende de num_people, por lo que
    aquí se muestra el precio con descuento asumiendo que el mínimo se cumple."""
    if not discount_active or not discount_type or not discount_value:
        return None
    if discount_type in (DiscountType.PERCENTAGE, DiscountType.VOLUME):
        return int(round(price_per_hour * (1 - float(discount_value) / 100)))
    return None


class SpaceScheduleOut(BaseModel):
    id: uuid.UUID
    day_of_week: int
    open_time: str
    close_time: str
    model_config = {"from_attributes": True}


class SpaceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    type: SpaceType
    description: str | None = Field(default=None, max_length=5000)
    address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=2, max_length=100)
    price_per_hour: Annotated[int, Field(gt=0, le=10_000_000)]
    capacity: Annotated[int, Field(gt=0, le=10_000)] = 1
    cancellation_policy: CancellationPolicy = CancellationPolicy.FLEXIBLE
    cancellation_hours: Annotated[int, Field(ge=0, le=720)] = 24
    amenities: list[str] = Field(default=[], max_length=50)

    @field_validator("name", "address", "city")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        result = _sanitize(v)
        return result if result else v

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str | None) -> str | None:
        return _sanitize(v, max_len=5000)

    @field_validator("amenities")
    @classmethod
    def sanitize_amenities(cls, v: list[str]) -> list[str]:
        return [(_sanitize(a, max_len=100) or "") for a in v if a.strip()]


class SpaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    price_per_hour: Annotated[int | None, Field(default=None, gt=0, le=10_000_000)] = None
    capacity: Annotated[int | None, Field(default=None, gt=0, le=10_000)] = None
    cancellation_policy: CancellationPolicy | None = None
    cancellation_hours: Annotated[int | None, Field(default=None, ge=0, le=720)] = None
    is_active: bool | None = None
    amenities: list[str] | None = None

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str | None) -> str | None:
        return _sanitize(v, max_len=255) if v else v

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str | None) -> str | None:
        return _sanitize(v, max_len=5000)

    # SC-001 — Descuentos / Ofertas
    discount_type: DiscountType | None = None
    discount_value: Annotated[float | None, Field(default=None, gt=0, le=100)] = None
    discount_active: bool | None = None
    discount_min_people: Annotated[int | None, Field(default=None, ge=1)] = None

    @model_validator(mode="after")
    def validate_discount(self) -> "SpaceUpdate":
        if self.discount_type == DiscountType.VOLUME and self.discount_active and not self.discount_min_people:
            raise ValueError("El descuento por volumen requiere 'discount_min_people'")
        return self


class HostOut(BaseModel):
    name: str
    bio: str | None = None
    model_config = {"from_attributes": True}


class SpaceImageOut(BaseModel):
    id: uuid.UUID
    url: str
    is_primary: bool
    display_order: int
    model_config = {"from_attributes": True}


class SpaceResponse(BaseModel):
    id: uuid.UUID
    slug: str | None = None
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
    # SC-001 — Descuentos / Ofertas
    discount_type: DiscountType | None = None
    discount_value: float | None = None
    discount_active: bool = False
    discount_min_people: int | None = None
    discounted_price: int | None = None
    images: list[SpaceImageOut] = []
    schedules: list[SpaceScheduleOut] = []
    amenities: list[str] = []
    host: HostOut | None = None
    model_config = {"from_attributes": True}

    @field_validator("amenities", mode="before")
    @classmethod
    def coerce_amenities(cls, v):
        if v and hasattr(v[0], "name"):
            return [a.name for a in v]
        return v

    @model_validator(mode="after")
    def fill_discounted_price(self) -> "SpaceResponse":
        if self.discounted_price is None:
            self.discounted_price = compute_discounted_price(
                self.price_per_hour, self.discount_active, self.discount_type, self.discount_value
            )
        return self

    @classmethod
    def from_orm_with_amenities(cls, space) -> "SpaceResponse":
        return cls.model_validate(space)


class SubSpaceItem(BaseModel):
    id: uuid.UUID
    slug: str | None = None
    name: str
    type: SpaceType
    description: str | None = None
    price_per_hour: int
    capacity: int
    rating: float
    is_active: bool
    primary_image: str | None = None
    amenities: list[str] = []
    discount_active: bool = False
    discount_type: DiscountType | None = None
    discount_value: float | None = None
    discounted_price: int | None = None
    model_config = {"from_attributes": True}

    @field_validator("amenities", mode="before")
    @classmethod
    def coerce_amenities(cls, v):
        if v and hasattr(v[0], "name"):
            return [a.name for a in v]
        return v

    @model_validator(mode="after")
    def fill_discounted_price(self) -> "SubSpaceItem":
        if self.discounted_price is None:
            self.discounted_price = compute_discounted_price(
                self.price_per_hour, self.discount_active, self.discount_type, self.discount_value
            )
        return self


class SpaceListItem(BaseModel):
    id: uuid.UUID
    slug: str | None = None
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
    # SC-001 — Descuentos / Ofertas
    discount_type: DiscountType | None = None
    discount_value: float | None = None
    discount_active: bool = False
    discount_min_people: int | None = None
    discounted_price: int | None = None
    model_config = {"from_attributes": True}


class SpaceFilters(BaseModel):
    lat: float | None = None
    lng: float | None = None
    radius_km: float = Field(default=10.0, gt=0)
    type: SpaceType | None = None
    city: str | None = None
    name: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    min_capacity: int | None = None
    on_offer: bool = False  # SC-001 — filtrar solo espacios con descuento activo
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


# --- Admin schemas ---

class AdminSpaceCreate(BaseModel):
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
    parent_id: uuid.UUID | None = None


class AdminSpaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3)
    slug: str | None = None
    type: SpaceType | None = None
    description: str | None = None
    address: str | None = None
    city: str | None = None
    price_per_hour: Annotated[int | None, Field(default=None, gt=0)] = None
    capacity: Annotated[int | None, Field(default=None, gt=0)] = None
    cancellation_policy: CancellationPolicy | None = None
    cancellation_hours: Annotated[int | None, Field(default=None, ge=0)] = None
    is_active: bool | None = None
    amenities: list[str] | None = None
    discount_type: DiscountType | None = None
    discount_value: Annotated[float | None, Field(default=None, gt=0, le=100)] = None
    discount_active: bool | None = None
    discount_min_people: Annotated[int | None, Field(default=None, ge=1)] = None


class AdminSpaceListItem(BaseModel):
    id: uuid.UUID
    slug: str | None = None
    name: str
    type: SpaceType
    city: str
    address: str
    price_per_hour: int
    capacity: int
    is_active: bool
    rating: float
    review_count: int
    parent_id: uuid.UUID | None = None
    primary_image: str | None = None
    provider_name: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
