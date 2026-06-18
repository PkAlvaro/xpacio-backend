from pydantic import BaseModel, Field


class SystemConfigOut(BaseModel):
    platform_fee_percent: float
    dispute_window_days: int
    pending_reservation_ttl_minutes: int
    maintenance_mode: bool

    model_config = {"from_attributes": True}


class SystemConfigUpdate(BaseModel):
    platform_fee_percent: float | None = Field(default=None, ge=0, le=100)
    dispute_window_days: int | None = Field(default=None, ge=1, le=30)
    pending_reservation_ttl_minutes: int | None = Field(default=None, ge=5, le=120)
    maintenance_mode: bool | None = None
