import uuid
from datetime import date, time, timedelta, datetime
from dataclasses import dataclass
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.space import SpaceSchedule
from app.models.reservation import Reservation
from app.constants import ReservationStatus
from app.utils.time_utils import slot_overlaps

logger = structlog.get_logger()


@dataclass
class TimeSlot:
    start: str  # "HH:MM"
    end: str
    available: bool


def _time_from_str(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def _add_minutes(t: time, minutes: int) -> time | None:
    dt = datetime.combine(date.today(), t) + timedelta(minutes=minutes)
    if dt.date() > date.today():
        return None
    return dt.time()


async def get_available_slots(
    space_id: uuid.UUID,
    target_date: date,
    slot_minutes: int,
    session: AsyncSession,
) -> list[TimeSlot]:
    day_of_week = target_date.weekday()  # 0=Mon, 6=Sun

    sched_result = await session.execute(
        select(SpaceSchedule).where(
            SpaceSchedule.space_id == space_id,
            SpaceSchedule.day_of_week == day_of_week,
        )
    )
    schedule = sched_result.scalar_one_or_none()
    if not schedule:
        return []

    open_t = _time_from_str(schedule.open_time)
    close_t = _time_from_str(schedule.close_time)

    # load confirmed/active reservations for this date
    res_result = await session.execute(
        select(Reservation).where(
            and_(
                Reservation.space_id == space_id,
                Reservation.date == target_date,
                Reservation.status.in_([
                    ReservationStatus.CONFIRMED,
                    ReservationStatus.ACTIVE,
                    ReservationStatus.PENDING,
                ]),
            )
        )
    )
    reservations = res_result.scalars().all()

    slots = []
    current = open_t
    while True:
        slot_end = _add_minutes(current, slot_minutes)
        if slot_end is None or slot_end > close_t:
            break

        occupied = any(
            slot_overlaps(current, slot_end, r.start_time, r.end_time)
            for r in reservations
        )
        slots.append(TimeSlot(
            start=current.strftime("%H:%M"),
            end=slot_end.strftime("%H:%M"),
            available=not occupied,
        ))
        current = slot_end

    return slots
