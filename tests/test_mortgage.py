import pytest

from modeling.mortgage import (
    calculate_mortgage,
    insurance_premium_rate,
    minimum_down_payment,
    periodic_interest_rate,
)


def test_minimum_down_payment_uses_current_price_tiers() -> None:
    assert minimum_down_payment(400_000) == 20_000
    assert minimum_down_payment(600_000) == 35_000
    assert minimum_down_payment(1_500_000) == 300_000


def test_insured_mortgage_adds_standard_premium_and_ontario_tax() -> None:
    estimate = calculate_mortgage(
        purchase_price=600_000,
        down_payment_percent=10,
        annual_rate_percent=6.09,
        amortization_years=25,
        payment_frequency="Monthly",
    )

    assert estimate.base_mortgage == 540_000
    assert insurance_premium_rate(0.90) == 0.031
    assert estimate.insurance_premium == pytest.approx(16_740)
    assert estimate.insurance_tax == pytest.approx(1_339.20)
    assert estimate.total_mortgage == pytest.approx(556_740)
    assert estimate.payment_amount > 3_000


def test_twenty_percent_down_payment_avoids_insurance() -> None:
    estimate = calculate_mortgage(
        purchase_price=900_000,
        down_payment_percent=20,
        annual_rate_percent=5,
        amortization_years=25,
    )

    assert estimate.insurance_premium == 0
    assert estimate.insurance_tax == 0
    assert estimate.total_mortgage == 720_000


def test_below_minimum_down_payment_is_rejected() -> None:
    with pytest.raises(ValueError, match="Minimum down payment"):
        calculate_mortgage(
            purchase_price=1_000_000,
            down_payment_percent=5,
            annual_rate_percent=5,
            amortization_years=25,
        )


def test_periodic_rate_supports_zero_interest() -> None:
    assert periodic_interest_rate(0, 12) == 0
