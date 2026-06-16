"""Tests unitarios — calculate_price y compute_discounted_price."""
from unittest.mock import MagicMock
from app.services.space_service import calculate_price
from app.schemas.space import compute_discounted_price
from app.constants import DiscountType


def _space(price, discount_active=False, discount_type=None, discount_value=None, discount_min_people=None):
    s = MagicMock()
    s.price_per_hour = price
    s.discount_active = discount_active
    s.discount_type = discount_type
    s.discount_value = discount_value
    s.discount_min_people = discount_min_people
    return s


class TestCalculatePrice:
    def test_no_discount(self):
        result = calculate_price(_space(10_000), hours=2, num_people=1)
        assert result["subtotal"] == 20_000
        assert result["discount"] == 0
        assert result["total"] == 20_000

    def test_percentage_discount(self):
        result = calculate_price(
            _space(10_000, True, DiscountType.PERCENTAGE, 20),
            hours=2, num_people=1,
        )
        assert result["subtotal"] == 20_000
        assert result["discount"] == 4_000
        assert result["total"] == 16_000

    def test_volume_discount_applies(self):
        result = calculate_price(
            _space(10_000, True, DiscountType.VOLUME, 10, discount_min_people=3),
            hours=1, num_people=5,
        )
        assert result["discount"] == 1_000
        assert result["total"] == 9_000

    def test_volume_discount_not_enough_people(self):
        result = calculate_price(
            _space(10_000, True, DiscountType.VOLUME, 10, discount_min_people=5),
            hours=1, num_people=2,
        )
        assert result["discount"] == 0
        assert result["total"] == 10_000

    def test_discount_inactive(self):
        result = calculate_price(
            _space(10_000, False, DiscountType.PERCENTAGE, 50),
            hours=1, num_people=1,
        )
        assert result["discount"] == 0

    def test_discount_never_exceeds_subtotal(self):
        result = calculate_price(
            _space(10_000, True, DiscountType.PERCENTAGE, 100),
            hours=1, num_people=1,
        )
        assert result["total"] == 0
        assert result["discount"] == 10_000

    def test_multiday_hours(self):
        result = calculate_price(_space(5_000), hours=24, num_people=1)
        assert result["subtotal"] == 120_000


class TestComputeDiscountedPrice:
    def test_no_discount(self):
        assert compute_discounted_price(10_000, False, None, None) is None

    def test_percentage(self):
        price = compute_discounted_price(10_000, True, DiscountType.PERCENTAGE, 10)
        assert price == 9_000

    def test_volume_same_formula(self):
        price = compute_discounted_price(10_000, True, DiscountType.VOLUME, 10)
        assert price == 9_000

    def test_missing_value(self):
        assert compute_discounted_price(10_000, True, DiscountType.PERCENTAGE, None) is None
