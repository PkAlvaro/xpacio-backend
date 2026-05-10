from datetime import datetime, date, time
import pytz
from app.constants import CHILE_TZ


def now_chile() -> datetime:
    return datetime.now(CHILE_TZ)


def to_chile(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(CHILE_TZ)


def combine_chile(d: date, t: time) -> datetime:
    return CHILE_TZ.localize(datetime.combine(d, t))


def slot_overlaps(start1: time, end1: time, start2: time, end2: time) -> bool:
    return start1 < end2 and end1 > start2
