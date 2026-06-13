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
from app.constants import DiscountType
from app.exceptions import NotFoundError, ForbiddenError
from app.services.geocoding_service import geocode
from app.services.redis_service import RedisService

logger = structlog.get_logger()


def calculate_price(space: Space, hours: int, num_people: int = 1) -> dict:
    """SC-001 — Cálculo de precio server-side con descuento aplicado.

    Devuelve {subtotal, discount, total} en CLP (enteros).
    - PERCENTAGE: descuenta `discount_value`% del subtotal siempre.
    - VOLUME: descuenta `discount_value`% solo si num_people >= discount_min_people.
    El precio base histórico (space.price_per_hour) nunca se altera.
    """
    base_subtotal = int(space.price_per_hour) * int(hours)
    discount = 0

    if space.discount_active and space.discount_type and space.discount_value:
        value = float(space.discount_value)
        if space.discount_type == DiscountType.PERCENTAGE:
            discount = int(round(base_subtotal * value / 100))
        elif space.discount_type == DiscountType.VOLUME:
            min_people = space.discount_min_people or 1
            if num_people >= min_people:
                discount = int(round(base_subtotal * value / 100))

    discount = max(0, min(discount, base_subtotal))
    total = base_subtotal - discount
    return {"subtotal": base_subtotal, "discount": discount, "total": total}


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

    # Horarios por defecto: lun–dom 08:00–22:00 (el anfitrión puede cambiarlos después)
    for day in range(7):
        session.add(SpaceSchedule(id=uuid.uuid4(), space_id=space.id, day_of_week=day, open_time="08:00", close_time="22:00"))

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
    if filters.on_offer:
        query = query.where(Space.discount_active == True)

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

        items.append(_to_list_item(space, primary_img, round(distance, 2) if distance else None))

    if filters.lat and filters.lng:
        items.sort(key=lambda s: s.distance_km or 999)

    return items, total


def _to_list_item(space: Space, primary_img: str | None = None, distance_km: float | None = None) -> SpaceListItem:
    from app.schemas.space import compute_discounted_price
    if primary_img is None and space.images:
        primary_img = next((img.url for img in space.images if img.is_primary), None)
    return SpaceListItem(
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
        distance_km=distance_km,
        discount_type=space.discount_type,
        discount_value=float(space.discount_value) if space.discount_value is not None else None,
        discount_active=space.discount_active,
        discount_min_people=space.discount_min_people,
        discounted_price=compute_discounted_price(
            space.price_per_hour, space.discount_active, space.discount_type, space.discount_value
        ),
    )


async def get_similar_spaces(space_id: uuid.UUID, session: AsyncSession, limit: int = 6) -> list[SpaceListItem]:
    """SC-002 (REQ-3.6) — Espacios similares, priorizando mismo tipo.

    Orden de prioridad:
      1. Mismo tipo (cancha → canchas, oficina → oficinas, etc.)
      2. Rellena con misma ciudad o precio ±30% si no hay suficientes del mismo tipo
      3. Fallback a los mejor calificados del catálogo general
    """
    base = await _load_space(session, space_id)
    price_low = base.price_per_hour * 0.7
    price_high = base.price_per_hour * 1.3
    spaces: list[Space] = []

    # 1. Mismo tipo (máxima prioridad)
    same_type = await session.execute(
        select(Space)
        .options(selectinload(Space.images))
        .where(Space.id != space_id, Space.is_active == True, Space.type == base.type)
        .order_by(Space.rating.desc(), Space.review_count.desc())
        .limit(limit)
    )
    spaces = list(same_type.scalars().all())

    # 2. Completar con misma ciudad o precio ±30% (distinto tipo)
    if len(spaces) < limit:
        have_ids = {s.id for s in spaces} | {space_id}
        secondary = await session.execute(
            select(Space)
            .options(selectinload(Space.images))
            .where(
                Space.id.notin_(have_ids),
                Space.is_active == True,
                (func.lower(Space.city) == base.city.lower())
                | and_(Space.price_per_hour >= price_low, Space.price_per_hour <= price_high),
            )
            .order_by(Space.rating.desc(), Space.review_count.desc())
            .limit(limit - len(spaces))
        )
        spaces.extend(secondary.scalars().all())

    # 3. Fallback general si aún faltan
    if len(spaces) < 3:
        have_ids = {s.id for s in spaces} | {space_id}
        fallback = await session.execute(
            select(Space)
            .options(selectinload(Space.images))
            .where(Space.is_active == True, Space.id.notin_(have_ids))
            .order_by(Space.rating.desc(), Space.review_count.desc())
            .limit(limit - len(spaces))
        )
        spaces.extend(fallback.scalars().all())

    return [_to_list_item(s) for s in spaces]


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


async def list_provider_spaces(user_id: uuid.UUID, session: AsyncSession) -> list[Space]:
    result = await session.execute(select(Provider).where(Provider.user_id == user_id))
    provider = result.scalar_one_or_none()
    if not provider:
        return []
    spaces_result = await session.execute(
        select(Space)
        .options(selectinload(Space.images), selectinload(Space.schedules), selectinload(Space.amenities))
        .where(Space.provider_id == provider.id)
        .order_by(Space.created_at.desc())
    )
    return spaces_result.scalars().all()


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
