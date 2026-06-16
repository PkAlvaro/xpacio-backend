import uuid
from datetime import date, time, timedelta, datetime
from dataclasses import dataclass
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.space import SpaceSchedule
from app.models.reservation import Reservation
from app.constants import ReservationStatus
from app.utils.time_utils import slot_overlaps, now_chile

logger = structlog.get_logger()


async def get_calendar_events(
    space_id: uuid.UUID,
    start_date: date,
    end_date: date,
    session: AsyncSession,
) -> list[dict]:
    """Return occupied reservations as FullCalendar-compatible events."""
    res_result = await session.execute(
        select(Reservation).where(
            and_(
                Reservation.space_id == space_id,
                # include multi-day reservations that overlap the requested range
                Reservation.date <= end_date,
                or_(Reservation.end_date == None, Reservation.end_date >= start_date),  # noqa: E711
                Reservation.status.in_([
                    ReservationStatus.CONFIRMED,
                    ReservationStatus.ACTIVE,
                    ReservationStatus.PENDING,
                ]),
                or_(
                    Reservation.status != ReservationStatus.PENDING,
                    Reservation.expires_at > now_chile(),
                ),
            )
        )
    )
    reservations = res_result.scalars().all()

    events = []
    for r in reservations:
        effective_end_date = r.end_date or r.date
        start_str = f"{r.date}T{str(r.start_time)[:5]}"
        end_str = f"{effective_end_date}T{str(r.end_time)[:5]}"
        events.append({
            "id": str(r.id),
            "title": "Ocupado",
            "start": start_str,
            "end": end_str,
            "color": "#ef4444",
            "textColor": "#fff",
            "display": "block",
        })
    return events


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
                # exclude expired PENDING reservations
                or_(
                    Reservation.status != ReservationStatus.PENDING,
                    Reservation.expires_at > now_chile(),
                ),
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
