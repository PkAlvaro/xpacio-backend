import uuid
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: Annotated[int, Field(ge=1, le=5)]
    comment: str | None = None


class ReviewResponse(BaseModel):
    id: uuid.UUID
    reservation_id: uuid.UUID
    space_id: uuid.UUID
    rating: int
    comment: str | None
    client_name: str
    created_at: datetime
    model_config = {"from_attributes": True}
