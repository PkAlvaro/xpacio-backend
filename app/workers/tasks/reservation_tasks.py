import asyncio
import structlog
from sqlalchemy import select, and_, update
from app.workers.celery_app import celery_app
from app.constants import ReservationStatus
from app.utils.time_utils import now_chile

logger = structlog.get_logger()


def _get_session():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.config import get_settings
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    return async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task(name="app.workers.tasks.reservation_tasks.expire_pending_reservations")
def expire_pending_reservations():
    asyncio.run(_expire_pending())


@celery_app.task(name="app.workers.tasks.reservation_tasks.transition_reservation_states")
def transition_reservation_states():
    asyncio.run(_transition_states())


async def _expire_pending():
    from app.models.reservation import Reservation
    SessionLocal = _get_session()
    now = now_chile()

    async with SessionLocal() as session:
        result = await session.execute(
            update(Reservation)
            .where(
                and_(
                    Reservation.status == ReservationStatus.PENDING,
                    Reservation.expires_at <= now,
                )
            )
            .values(status=ReservationStatus.EXPIRED)
            .returning(Reservation.id)
        )
        expired_ids = result.fetchall()
        await session.commit()

    if expired_ids:
        logger.info("reservations_expired", count=len(expired_ids))


async def _transition_states():
    from app.models.reservation import Reservation
    from datetime import datetime
    SessionLocal = _get_session()
    now = now_chile()
    today = now.date()
    current_time = now.time()

    async with SessionLocal() as session:
        # confirmed → active when start_time passed
        await session.execute(
            update(Reservation)
            .where(
                and_(
                    Reservation.status == ReservationStatus.CONFIRMED,
                    Reservation.date == today,
                    Reservation.start_time <= current_time,
                )
            )
            .values(status=ReservationStatus.ACTIVE)
        )

        # also past dates still confirmed
        await session.execute(
            update(Reservation)
            .where(
                and_(
                    Reservation.status == ReservationStatus.CONFIRMED,
                    Reservation.date < today,
                )
            )
            .values(status=ReservationStatus.ACTIVE)
        )

        # active → finished when end_time passed
        await session.execute(
            update(Reservation)
            .where(
                and_(
                    Reservation.status == ReservationStatus.ACTIVE,
                    Reservation.date == today,
                    Reservation.end_time <= current_time,
                )
            )
            .values(status=ReservationStatus.FINISHED)
        )

        await session.execute(
            update(Reservation)
            .where(
                and_(
                    Reservation.status == ReservationStatus.ACTIVE,
                    Reservation.date < today,
                )
            )
            .values(status=ReservationStatus.FINISHED)
        )

        await session.commit()
    logger.debug("reservation_transitions_done")
