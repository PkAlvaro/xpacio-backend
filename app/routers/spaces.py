import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.database import get_session
from app.dependencies import get_redis, get_current_user, require_role
from app.constants import UserRole
from app.schemas.space import (
    SpaceCreate, SpaceUpdate, SpaceResponse, SpaceListItem,
    SpaceFilters, ScheduleCreate, SpaceScheduleOut,
)
from app.services import space_service

router = APIRouter(prefix="/api/v1/spaces", tags=["spaces"])


@router.get("", response_model=dict)
async def list_spaces(
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    radius_km: float = Query(default=10.0),
    type: str | None = Query(default=None),
    city: str | None = Query(default=None),
    min_price: int | None = Query(default=None),
    max_price: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    from app.constants import SpaceType
    filters = SpaceFilters(
        lat=lat, lng=lng, radius_km=radius_km,
        type=SpaceType(type) if type else None,
        city=city, min_price=min_price, max_price=max_price,
        page=page, page_size=page_size,
    )
    items, total = await space_service.list_spaces(filters, session)
    return {
        "success": True,
        "data": [i.model_dump() for i in items],
        "meta": {"total": total, "page": page, "page_size": page_size},
    }


@router.post("", response_model=dict, status_code=201)
async def create_space(
    data: SpaceCreate,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    import uuid as _uuid
    from sqlalchemy import select
    from app.models.provider import Provider
    result = await session.execute(select(Provider).where(Provider.user_id == user.id))
    provider = result.scalar_one_or_none()
    if not provider:
        provider = Provider(id=_uuid.uuid4(), user_id=user.id)
        session.add(provider)
        await session.flush()

    space = await space_service.create_space(data, provider.id, session, redis)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.get("/{space_id}", response_model=dict)
async def get_space(space_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    space = await space_service.get_space(space_id, session)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.patch("/{space_id}", response_model=dict)
async def update_space(
    space_id: uuid.UUID,
    data: SpaceUpdate,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    space = await space_service.update_space(space_id, data, user.id, session)
    return {"success": True, "data": SpaceResponse.from_orm_with_amenities(space).model_dump()}


@router.delete("/{space_id}", status_code=204)
async def delete_space(
    space_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    await space_service.delete_space(space_id, user.id, session)


@router.put("/{space_id}/schedules", response_model=dict)
async def set_schedules(
    space_id: uuid.UUID,
    schedules: list[ScheduleCreate],
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(UserRole.PROVIDER, UserRole.ADMIN)),
):
    result = await space_service.set_schedules(space_id, schedules, user.id, session)
    return {"success": True, "data": [SpaceScheduleOut.model_validate(s).model_dump() for s in result]}


@router.get("/{space_id}/schedules", response_model=dict)
async def get_schedules(space_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    space = await space_service.get_space(space_id, session)
    return {"success": True, "data": [SpaceScheduleOut.model_validate(s).model_dump() for s in space.schedules]}
