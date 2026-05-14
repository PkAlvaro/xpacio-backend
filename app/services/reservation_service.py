import uuid
import math
import structlog
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from app.models.reservation import Reservation
from app.models.space import Space
from app.constants import ReservationStatus, CancellationPolicy, PENDING_RESERVATION_TTL_MINUTES
from app.exceptions import ConflictError, NotFoundError, ForbiddenError, DomainException
from app.schemas.reservation import ReservationCreate
from app.utils.time_utils import now_chile, combine_chile
from app.services import calendar_service

logger = structlog.get_logger()


async def create_reservation(
    data: ReservationCreate,
    client_id: uuid.UUID,
    session: AsyncSession,
) -> Reservation:
    # load space to get price
    space_result = await session.execute(select(Space).where(Space.id == data.space_id, Space.is_active == True))
    space = space_result.scalar_one_or_none()
    if not space:
        raise NotFoundError("Espacio")

    # calculate total
    start_dt = combine_chile(data.date, data.start_time)
    end_dt = combine_chile(data.date, data.end_time)
    duration_minutes = (end_dt - start_dt).seconds // 60
    hours = math.ceil(duration_minutes / 60)
    subtotal = space.price_per_hour * hours
    total = subtotal  # no service fee for MVP

    expires_at = now_chile() + timedelta(minutes=PENDING_RESERVATION_TTL_MINUTES)

    reservation = Reservation(
        id=uuid.uuid4(),
        space_id=data.space_id,
        client_id=client_id,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        hours=hours,
        subtotal=subtotal,
        service_fee=0,
        total=total,
        status=ReservationStatus.PENDING,
        expires_at=expires_at,
    )
    session.add(reservation)

    try:
        await session.commit()
        await session.refresh(reservation)
        logger.info("reservation_created", id=str(reservation.id))
        return reservation
    except IntegrityError as e:
        await session.rollback()
        if "excl_no_overlap" in str(e.orig):
            raise ConflictError("El horario seleccionado no está disponible")
        raise


async def confirm_reservation(reservation_id: uuid.UUID, session: AsyncSession) -> Reservation:
    reservation = await _get_or_raise(reservation_id, session)
    if reservation.status != ReservationStatus.PENDING:
        raise DomainException(f"No se puede confirmar una reserva en estado '{reservation.status}'")
    reservation.status = ReservationStatus.CONFIRMED
    await session.commit()
    await session.refresh(reservation)

    # Google Calendar — falla silenciosa si no configurado
    await _sync_calendar_on_confirm(reservation, session)

    return reservation


async def _sync_calendar_on_confirm(reservation: Reservation, session: AsyncSession) -> None:
    from app.models.user import User

    try:
        await session.refresh(reservation, ["space", "client"])
        space = reservation.space
        client = reservation.client

        # obtener email del proveedor
        from app.models.provider import Provider
        prov_result = await session.execute(
            select(Provider).where(Provider.id == space.provider_id)
        )
        provider = prov_result.scalar_one_or_none()
        prov_user = None
        if provider:
            prov_user_result = await session.execute(
                select(User).where(User.id == provider.user_id)
            )
            prov_user = prov_user_result.scalar_one_or_none()

        event_id = await calendar_service.create_event(
            reservation_id=str(reservation.id),
            space_name=space.name,
            date=str(reservation.date),
            start_time=reservation.start_time,
            end_time=reservation.end_time,
            total=reservation.total,
            client_email=client.email,
            provider_email=prov_user.email if prov_user else "",
        )
        if event_id:
            reservation.google_event_id = event_id
            await session.commit()
    except Exception as e:
        logger.warning("calendar_sync_failed", reservation_id=str(reservation.id), error=str(e))


async def cancel_reservation(
    reservation_id: uuid.UUID,
    user_id: uuid.UUID,
    reason: str | None,
    session: AsyncSession,
) -> Reservation:
    reservation = await _get_or_raise(reservation_id, session)

    if str(reservation.client_id) != str(user_id):
        # allow provider too — covered by caller
        raise ForbiddenError("No puedes cancelar esta reserva")

    if reservation.status not in (ReservationStatus.PENDING, ReservationStatus.CONFIRMED):
        raise DomainException(f"No se puede cancelar una reserva en estado '{reservation.status}'")

    event_id = reservation.google_event_id
    now = now_chile()
    reservation.status = ReservationStatus.CANCELLED
    reservation.cancelled_at = now
    reservation.cancellation_reason = reason
    reservation.google_event_id = None
    await session.commit()
    logger.info("reservation_cancelled", id=str(reservation_id))

    if event_id:
        await calendar_service.delete_event(event_id)

    return reservation


async def list_client_reservations(
    client_id: uuid.UUID,
    session: AsyncSession,
    status: ReservationStatus | None = None,
) -> list[Reservation]:
    query = select(Reservation).where(Reservation.client_id == client_id)
    if status:
        query = query.where(Reservation.status == status)
    query = query.order_by(Reservation.date.desc())
    result = await session.execute(query)
    return result.scalars().all()


async def get_reservation(
    reservation_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> Reservation:
    reservation = await _get_or_raise(reservation_id, session)
    if str(reservation.client_id) != str(user_id):
        raise ForbiddenError("Acceso denegado")
    return reservation


async def list_incoming_reservations(
    provider_user_id: uuid.UUID,
    session: AsyncSession,
    status: ReservationStatus | None = None,
) -> list[Reservation]:
    from app.models.provider import Provider
    from app.models.space import Space

    prov_result = await session.execute(select(Provider).where(Provider.user_id == provider_user_id))
    provider = prov_result.scalar_one_or_none()
    if not provider:
        return []

    space_result = await session.execute(select(Space.id).where(Space.provider_id == provider.id))
    space_ids = [row[0] for row in space_result.all()]
    if not space_ids:
        return []

    query = select(Reservation).where(Reservation.space_id.in_(space_ids))
    if status:
        query = query.where(Reservation.status == status)
    query = query.order_by(Reservation.date.desc())
    result = await session.execute(query)
    return result.scalars().all()


async def _get_or_raise(reservation_id: uuid.UUID, session: AsyncSession) -> Reservation:
    result = await session.execute(select(Reservation).where(Reservation.id == reservation_id))
    reservation = result.scalar_one_or_none()
    if not reservation:
        raise NotFoundError("Reserva")
    return reservation
