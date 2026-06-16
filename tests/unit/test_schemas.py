"""Tests unitarios — validaciones de schemas Pydantic."""
import pytest
from datetime import date, time
from app.schemas.reservation import ReservationCreate


def _valid_payload(**overrides):
    base = dict(
        space_id="00000000-0000-0000-0000-000000000001",
        date=date(2026, 8, 1),
        start_time=time(10, 0),
        end_time=time(12, 0),
        num_people=2,
    )
    base.update(overrides)
    return base


class TestReservationCreate:
    def test_valid(self):
        r = ReservationCreate(**_valid_payload())
        assert r.num_people == 2

    def test_end_before_start_raises(self):
        with pytest.raises(Exception):
            ReservationCreate(**_valid_payload(start_time=time(14, 0), end_time=time(12, 0)))

    def test_equal_start_end_raises(self):
        with pytest.raises(Exception):
            ReservationCreate(**_valid_payload(start_time=time(10, 0), end_time=time(10, 0)))

    def test_num_people_zero_raises(self):
        with pytest.raises(Exception):
            ReservationCreate(**_valid_payload(num_people=0))

    def test_num_people_negative_raises(self):
        with pytest.raises(Exception):
            ReservationCreate(**_valid_payload(num_people=-1))

    def test_end_date_before_start_date_raises(self):
        with pytest.raises(Exception):
            ReservationCreate(**_valid_payload(
                date=date(2026, 8, 5),
                end_date=date(2026, 8, 1),
            ))

    def test_multiday_valid(self):
        r = ReservationCreate(**_valid_payload(
            end_date=date(2026, 8, 3),
            start_time=time(10, 0),
            end_time=time(10, 0),
        ))
        assert r.end_date == date(2026, 8, 3)

    def test_default_num_people(self):
        payload = _valid_payload()
        payload.pop("num_people")
        r = ReservationCreate(**payload)
        assert r.num_people == 1
