import uuid
import math
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
import redis.asyncio as aioredis

from app.models.space import Space, SpaceSchedule, SpaceImage, SpaceAmenity
from app.models.provider import Provider
from app.schemas.space import SpaceCreate, SpaceUpdate, SpaceFilters, ScheduleCreate, SpaceListItem
from app.exceptions import NotFoundError, ForbiddenError
from app.services.geocoding_service import geocode
from app.services.redis_service import RedisService

logger = structlog.get_logger()


async def _load_space(session: AsyncSession, space_id: uuid.UUID) -> Space:
    result = await session.execute(
        select(Space)
        .options(
            selectinload(Space.images),
            selectinload(Space.schedules),
            selectinload(Space.amenities),
        )
        .where(Space.id == space_id)
    )
    space = result.scalar_one_or_none()
    if not space:
        raise NotFoundError("Espacio")
    return space


async def create_space(
    data: SpaceCreate,
    provider_id: uuid.UUID,
    session: AsyncSession,
    redis: aioredis.Redis,
) -> Space:
    redis_svc = RedisService(redis)
    coords = await geocode(f"{data.address}, {data.city}, Chile", redis_svc)

    space = Space(
        id=uuid.uuid4(),
        provider_id=provider_id,
        name=data.name,
        type=data.type,
        description=data.description,
        address=data.address,
        city=data.city,
        lat=coords[0] if coords else None,
        lng=coords[1] if coords else None,
        price_per_hour=data.price_per_hour,
        capacity=data.capacity,
        cancellation_policy=data.cancellation_policy,
        cancellation_hours=data.cancellation_hours,
    )
    session.add(space)

    for name in data.amenities:
        session.add(SpaceAmenity(id=uuid.uuid4(), space_id=space.id, name=name))

    await session.commit()
    return await _load_space(session, space.id)


async def get_space(space_id: uuid.UUID, session: AsyncSession) -> Space:
    return await _load_space(session, space_id)


async def list_spaces(filters: SpaceFilters, session: AsyncSession) -> tuple[list[SpaceListItem], int]:
    query = select(Space).where(Space.is_active == True)

    if filters.type:
        query = query.where(Space.type == filters.type)
    if filters.city:
        query = query.where(func.lower(Space.city) == filters.city.lower())
    if filters.min_price:
        query = query.where(Space.price_per_hour >= filters.min_price)
    if filters.max_price:
        query = query.where(Space.price_per_hour <= filters.max_price)

    count_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    query = query.options(selectinload(Space.images)).offset(
        (filters.page - 1) * filters.page_size
    ).limit(filters.page_size)

    result = await session.execute(query)
    spaces = result.scalars().all()

    items = []
    for space in spaces:
        primary_img = next((img.url for img in space.images if img.is_primary), None)
        distance = None
        if filters.lat and filters.lng and space.lat and space.lng:
            distance = _haversine(filters.lat, filters.lng, float(space.lat), float(space.lng))
            if distance > filters.radius_km:
                continue

        items.append(SpaceListItem(
            id=space.id,
            name=space.name,
            type=space.type,
            city=space.city,
            address=space.address,
            lat=float(space.lat) if space.lat else None,
            lng=float(space.lng) if space.lng else None,
            price_per_hour=space.price_per_hour,
            capacity=space.capacity,
            rating=float(space.rating),
            review_count=space.review_count,
            is_active=space.is_active,
            primary_image=primary_img,
            distance_km=round(distance, 2) if distance else None,
        ))

    if filters.lat and filters.lng:
        items.sort(key=lambda s: s.distance_km or 999)

    return items, total


async def update_space(
    space_id: uuid.UUID,
    data: SpaceUpdate,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> Space:
    space = await _load_space(session, space_id)
    await _assert_owner(space, user_id, session)

    for field, value in data.model_dump(exclude_unset=True, exclude={"amenities"}).items():
        setattr(space, field, value)

    if data.amenities is not None:
        for amenity in space.amenities:
            await session.delete(amenity)
        for name in data.amenities:
            session.add(SpaceAmenity(id=uuid.uuid4(), space_id=space.id, name=name))

    await session.commit()
    return await _load_space(session, space.id)


async def delete_space(
    space_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> None:
    space = await _load_space(session, space_id)
    await _assert_owner(space, user_id, session)
    space.is_active = False
    await session.commit()


async def set_schedules(
    space_id: uuid.UUID,
    schedules: list[ScheduleCreate],
    user_id: uuid.UUID,
    session: AsyncSession,
) -> list[SpaceSchedule]:
    space = await _load_space(session, space_id)
    await _assert_owner(space, user_id, session)

    for s in space.schedules:
        await session.delete(s)

    new_schedules = []
    for sc in schedules:
        if sc.open_time >= sc.close_time:
            from app.exceptions import DomainException
            raise DomainException(f"Horario inválido para día {sc.day_of_week}: open_time debe ser menor que close_time")
        obj = SpaceSchedule(
            id=uuid.uuid4(),
            space_id=space_id,
            day_of_week=sc.day_of_week,
            open_time=sc.open_time,
            close_time=sc.close_time,
        )
        session.add(obj)
        new_schedules.append(obj)

    await session.commit()
    return new_schedules


async def _assert_owner(space: Space, user_id: uuid.UUID, session: AsyncSession) -> None:
    result = await session.execute(
        select(Provider).where(Provider.id == space.provider_id, Provider.user_id == user_id)
    )
    if not result.scalar_one_or_none():
        raise ForbiddenError("No tienes permiso para modificar este espacio")


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))
