import uuid
import math
import re
import secrets
import unicodedata
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
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


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


async def _unique_slug(name: str, city: str, session: AsyncSession, exclude_id: uuid.UUID | None = None) -> str:
    base = _slugify(f"{name}-{city}")[:80]
    slug = base
    for _ in range(10):
        q = select(Space.id).where(Space.slug == slug)
        if exclude_id:
            q = q.where(Space.id != exclude_id)
        if not await session.scalar(q):
            return slug
        slug = f"{base}-{secrets.token_hex(2)}"
    return f"{base}-{secrets.token_hex(4)}"


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
    slug = await _unique_slug(data.name, data.city, session)

    space = Space(
        id=uuid.uuid4(),
        provider_id=provider_id,
        name=data.name,
        slug=slug,
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


async def get_space_by_slug(slug: str, session: AsyncSession) -> Space:
    result = await session.execute(
        select(Space)
        .options(selectinload(Space.images), selectinload(Space.schedules), selectinload(Space.amenities))
        .where(Space.slug == slug)
    )
    space = result.scalar_one_or_none()
    if not space:
        raise NotFoundError("Espacio")
    return space


async def resolve_space(id_or_slug: str, session: AsyncSession) -> Space:
    try:
        return await get_space(uuid.UUID(id_or_slug), session)
    except ValueError:
        return await get_space_by_slug(id_or_slug, session)


async def list_spaces(filters: SpaceFilters, session: AsyncSession) -> tuple[list[SpaceListItem], int]:
    query = select(Space).where(Space.is_active.is_(True), Space.parent_id.is_(None))

    if filters.type:
        query = query.where(Space.type == filters.type)
    if filters.city:
        query = query.where(func.lower(Space.city) == filters.city.lower())
    if filters.min_price:
        query = query.where(Space.price_per_hour >= filters.min_price)
    if filters.max_price:
        query = query.where(Space.price_per_hour <= filters.max_price)
    if filters.name:
        query = query.where(func.lower(Space.name).contains(filters.name.lower()))
    if filters.min_capacity:
        query = query.where(Space.capacity >= filters.min_capacity)
    if filters.on_offer:
        query = query.where(Space.discount_active.is_(True))

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
        .where(Space.id != space_id, Space.is_active.is_(True), Space.type == base.type)
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
                Space.is_active.is_(True),
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
            .where(Space.is_active.is_(True), Space.id.notin_(have_ids))
            .order_by(Space.rating.desc(), Space.review_count.desc())
            .limit(limit - len(spaces))
        )
        spaces.extend(fallback.scalars().all())

    return [_to_list_item(s) for s in spaces]


async def suggest_spaces(q: str, session: AsyncSession, limit: int = 8) -> list[dict]:
    """Fuzzy name search usando pg_trgm similarity + ILIKE fallback.

    Retorna id, name, type, city, address, primary_image, rating ordenados por score desc.
    Umbral bajo (0.05) para capturar coincidencias parciales de nombres cortos.
    """
    q = q.strip()
    if not q:
        return []

    sim_expr = func.similarity(Space.name, q)
    result = await session.execute(
        select(Space, sim_expr.label("score"))
        .options(selectinload(Space.images))
        .where(
            Space.is_active.is_(True),
            Space.parent_id.is_(None),
            or_(
                sim_expr > 0.05,
                func.lower(Space.name).contains(q.lower()),
            ),
        )
        .order_by(sim_expr.desc(), Space.rating.desc())
        .limit(limit)
    )
    rows = result.all()

    suggestions = []
    for space, _score in rows:
        primary = next((img.url for img in space.images if img.is_primary), None)
        if not primary and space.images:
            primary = space.images[0].url
        suggestions.append({
            "id": str(space.id),
            "slug": space.slug,
            "name": space.name,
            "type": space.type.value,
            "city": space.city,
            "address": space.address,
            "primary_image": primary,
            "rating": float(space.rating),
            "price_per_hour": space.price_per_hour,
        })
    return suggestions


async def list_sub_spaces(space_id: uuid.UUID, session: AsyncSession) -> list[Space]:
    result = await session.execute(
        select(Space)
        .options(selectinload(Space.images), selectinload(Space.amenities))
        .where(Space.parent_id == space_id, Space.is_active.is_(True))
        .order_by(Space.price_per_hour.asc())
    )
    return list(result.scalars().all())


async def update_space(
    space_id: uuid.UUID,
    data: SpaceUpdate,
    user_id: uuid.UUID,
    session: AsyncSession,
    redis=None,
) -> Space:
    space = await _load_space(session, space_id)
    await _assert_owner(space, user_id, session)

    address_changed = (data.address is not None and data.address != space.address) or \
                      (data.city is not None and data.city != space.city)

    for field, value in data.model_dump(exclude_unset=True, exclude={"amenities"}).items():
        setattr(space, field, value)

    if address_changed:
        addr = data.address or space.address
        city = data.city or space.city
        coords = await geocode(f"{addr}, {city}, Chile", redis)
        if coords:
            space.lat, space.lng = coords[0], coords[1]

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
    skip_owner_check: bool = False,
) -> list[SpaceSchedule]:
    space = await _load_space(session, space_id)
    if not skip_owner_check:
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


# --- Admin functions ---

async def admin_list_spaces(
    session: AsyncSession,
    q: str | None = None,
    active_only: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list, int]:
    from app.schemas.space import AdminSpaceListItem
    from app.models.user import User

    query = select(Space).where(Space.parent_id.is_(None))
    if q:
        query = query.where(func.lower(Space.name).contains(q.lower()))
    if active_only is not None:
        query = query.where(Space.is_active == active_only)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    query = (
        query
        .options(selectinload(Space.images))
        .order_by(Space.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    spaces = list((await session.execute(query)).scalars().all())

    provider_ids = [s.provider_id for s in spaces]
    providers = {}
    if provider_ids:
        prov_res = await session.execute(
            select(Provider, User).join(User, Provider.user_id == User.id)
            .where(Provider.id.in_(provider_ids))
        )
        for prov, user in prov_res.all():
            providers[prov.id] = user.name

    items = []
    for s in spaces:
        primary = next((img.url for img in s.images if img.is_primary), None) or (s.images[0].url if s.images else None)
        items.append(AdminSpaceListItem(
            id=s.id,
            slug=s.slug,
            name=s.name,
            type=s.type,
            city=s.city,
            address=s.address,
            price_per_hour=s.price_per_hour,
            capacity=s.capacity,
            is_active=s.is_active,
            rating=float(s.rating),
            review_count=s.review_count,
            parent_id=s.parent_id,
            primary_image=primary,
            provider_name=providers.get(s.provider_id),
            created_at=s.created_at,
        ))
    return items, total


async def admin_create_space(
    data,
    provider_id: uuid.UUID,
    session: AsyncSession,
    redis: aioredis.Redis,
) -> Space:
    redis_svc = RedisService(redis)
    coords = await geocode(f"{data.address}, {data.city}, Chile", redis_svc)
    slug = await _unique_slug(data.name, data.city, session)

    space = Space(
        id=uuid.uuid4(),
        provider_id=provider_id,
        name=data.name,
        slug=slug,
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
        parent_id=getattr(data, "parent_id", None),
    )
    session.add(space)
    for name in data.amenities:
        session.add(SpaceAmenity(id=uuid.uuid4(), space_id=space.id, name=name))
    for day in range(7):
        session.add(SpaceSchedule(id=uuid.uuid4(), space_id=space.id, day_of_week=day, open_time="08:00", close_time="22:00"))
    await session.commit()
    return await _load_space(session, space.id)


async def admin_update_space(space_id: uuid.UUID, data, session: AsyncSession, redis: aioredis.Redis | None = None) -> Space:
    space = await _load_space(session, space_id)
    update_data = data.model_dump(exclude_unset=True, exclude={"amenities"})

    if "address" in update_data or "city" in update_data:
        addr = update_data.get("address", space.address)
        city = update_data.get("city", space.city)
        if redis:
            redis_svc = RedisService(redis)
            coords = await geocode(f"{addr}, {city}, Chile", redis_svc)
            if coords:
                update_data["lat"] = coords[0]
                update_data["lng"] = coords[1]

    if "name" in update_data or "city" in update_data:
        new_name = update_data.get("name", space.name)
        new_city = update_data.get("city", space.city)
        if not update_data.get("slug"):
            update_data["slug"] = await _unique_slug(new_name, new_city, session, exclude_id=space_id)

    for field, value in update_data.items():
        setattr(space, field, value)

    if data.amenities is not None:
        for amenity in space.amenities:
            await session.delete(amenity)
        for name in data.amenities:
            session.add(SpaceAmenity(id=uuid.uuid4(), space_id=space.id, name=name))

    await session.commit()
    return await _load_space(session, space.id)


async def admin_hard_delete_space(space_id: uuid.UUID, session: AsyncSession) -> None:
    space = await _load_space(session, space_id)
    await session.delete(space)
    await session.commit()


async def upload_space_image(
    space_id: uuid.UUID,
    file,
    session: AsyncSession,
    set_primary: bool = False,
) -> SpaceImage:
    from app.services.storage_service import upload_file
    url = await upload_file(file, folder=f"spaces/{space_id}")

    existing = (await session.execute(select(SpaceImage).where(SpaceImage.space_id == space_id))).scalars().all()
    is_primary = set_primary or len(existing) == 0
    if is_primary:
        for img in existing:
            img.is_primary = False

    img = SpaceImage(
        id=uuid.uuid4(),
        space_id=space_id,
        url=url,
        is_primary=is_primary,
        display_order=len(existing),
    )
    session.add(img)
    await session.commit()
    await session.refresh(img)
    return img


async def delete_space_image(space_id: uuid.UUID, image_id: uuid.UUID, session: AsyncSession) -> None:
    from app.services.storage_service import delete_file
    from app.exceptions import NotFoundError

    result = await session.execute(
        select(SpaceImage).where(SpaceImage.id == image_id, SpaceImage.space_id == space_id)
    )
    img = result.scalar_one_or_none()
    if not img:
        raise NotFoundError("Imagen")

    if img.url.startswith("/storage/"):
        key = img.url.removeprefix("/storage/")
        delete_file(key)

    was_primary = img.is_primary
    await session.delete(img)
    await session.flush()

    if was_primary:
        remaining = (await session.execute(
            select(SpaceImage).where(SpaceImage.space_id == space_id).order_by(SpaceImage.display_order)
        )).scalars().first()
        if remaining:
            remaining.is_primary = True

    await session.commit()


async def set_primary_image(space_id: uuid.UUID, image_id: uuid.UUID, session: AsyncSession) -> None:
    imgs = (await session.execute(
        select(SpaceImage).where(SpaceImage.space_id == space_id)
    )).scalars().all()
    for img in imgs:
        img.is_primary = (img.id == image_id)
    await session.commit()


async def admin_stats(session: AsyncSession) -> dict:
    from datetime import date, timedelta
    from sqlalchemy import cast, Date as SADate
    from app.models.reservation import Reservation
    from app.models.payment import Payment
    from app.models.dispute import Dispute
    from app.models.user import User
    from app.constants import PaymentStatus, DisputeStatus, ReservationStatus

    total_spaces = (await session.execute(select(func.count()).select_from(Space).where(Space.parent_id.is_(None)))).scalar_one()
    active_spaces = (await session.execute(select(func.count()).select_from(Space).where(Space.is_active.is_(True), Space.parent_id.is_(None)))).scalar_one()
    total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    total_reservations = (await session.execute(select(func.count()).select_from(Reservation))).scalar_one()

    revenue_row = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == PaymentStatus.PAID)
    )
    total_revenue = revenue_row.scalar_one()

    thirty_days_ago = date.today() - timedelta(days=29)
    revenue_30d_row = await session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.status == PaymentStatus.PAID, cast(Payment.created_at, SADate) >= thirty_days_ago)
    )
    revenue_30d = revenue_30d_row.scalar_one()

    pending_disputes = (await session.execute(
        select(func.count()).select_from(Dispute).where(Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]))
    )).scalar_one()

    daily_rows = await session.execute(
        select(
            cast(Reservation.created_at, SADate).label("day"),
            func.count().label("count"),
        )
        .where(cast(Reservation.created_at, SADate) >= thirty_days_ago)
        .group_by(cast(Reservation.created_at, SADate))
        .order_by(cast(Reservation.created_at, SADate))
    )
    daily_data = [{"date": str(row.day), "reservations": row.count} for row in daily_rows]

    return {
        "total_spaces": total_spaces,
        "active_spaces": active_spaces,
        "total_users": total_users,
        "total_reservations": total_reservations,
        "total_revenue": total_revenue,
        "revenue_30d": revenue_30d,
        "pending_disputes": pending_disputes,
        "daily_reservations": daily_data,
    }
