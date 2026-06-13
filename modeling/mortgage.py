"""Canadian mortgage payment and loan-insurance estimates."""

from __future__ import annotations

from dataclasses import dataclass


PAYMENTS_PER_YEAR = {
    "Monthly": 12,
    "Bi-weekly": 26,
    "Weekly": 52,
}
ONTARIO_INSURANCE_TAX_RATE = 0.08


@dataclass(frozen=True)
class MortgageEstimate:
    """Mortgage principal, insurance, payments, and total financing cost."""

    purchase_price: float
    down_payment: float
    minimum_down_payment: float
    base_mortgage: float
    insurance_premium: float
    insurance_tax: float
    total_mortgage: float
    payment_amount: float
    payment_frequency: str
    total_payments: int
    total_interest: float


def minimum_down_payment(purchase_price: float) -> float:
    """Return Canada's standard minimum down payment for an owner-occupied home."""
    if purchase_price <= 0:
        raise ValueError("purchase_price must be greater than zero")
    if purchase_price <= 500_000:
        return purchase_price * 0.05
    if purchase_price < 1_500_000:
        return 25_000 + (purchase_price - 500_000) * 0.10
    return purchase_price * 0.20


def insurance_premium_rate(loan_to_value: float) -> float:
    """Return the standard CMHC premium rate for a purchase mortgage."""
    if loan_to_value <= 0.65:
        return 0.006
    if loan_to_value <= 0.75:
        return 0.017
    if loan_to_value <= 0.80:
        return 0.024
    if loan_to_value <= 0.85:
        return 0.028
    if loan_to_value <= 0.90:
        return 0.031
    if loan_to_value <= 0.95:
        return 0.04
    raise ValueError("loan_to_value cannot exceed 95%")


def periodic_interest_rate(
    annual_rate_percent: float,
    payments_per_year: int,
) -> float:
    """Convert a Canadian nominal semi-annual rate to a payment-period rate."""
    if annual_rate_percent < 0:
        raise ValueError("annual_rate_percent cannot be negative")
    if payments_per_year <= 0:
        raise ValueError("payments_per_year must be greater than zero")
    nominal_rate = annual_rate_percent / 100
    return (1 + nominal_rate / 2) ** (2 / payments_per_year) - 1


def calculate_mortgage(
    *,
    purchase_price: float,
    down_payment_percent: float,
    annual_rate_percent: float,
    amortization_years: int,
    payment_frequency: str = "Monthly",
) -> MortgageEstimate:
    """Calculate an insured or uninsured Canadian mortgage estimate."""
    if payment_frequency not in PAYMENTS_PER_YEAR:
        raise ValueError(f"Unsupported payment frequency: {payment_frequency}")
    if not 0 < down_payment_percent <= 100:
        raise ValueError("down_payment_percent must be between 0 and 100")
    if amortization_years <= 0:
        raise ValueError("amortization_years must be greater than zero")

    down_payment = purchase_price * down_payment_percent / 100
    minimum = minimum_down_payment(purchase_price)
    if down_payment + 0.01 < minimum:
        raise ValueError(
            f"Minimum down payment is ${minimum:,.0f} "
            f"({minimum / purchase_price:.1%})"
        )

    base_mortgage = purchase_price - down_payment
    loan_to_value = base_mortgage / purchase_price
    insurance_premium = 0.0
    if loan_to_value > 0.80:
        insurance_premium = base_mortgage * insurance_premium_rate(loan_to_value)

    insurance_tax = insurance_premium * ONTARIO_INSURANCE_TAX_RATE
    total_mortgage = base_mortgage + insurance_premium
    payments_per_year = PAYMENTS_PER_YEAR[payment_frequency]
    total_payments = payments_per_year * amortization_years
    rate = periodic_interest_rate(annual_rate_percent, payments_per_year)
    if rate == 0:
        payment_amount = total_mortgage / total_payments
    else:
        payment_amount = (
            total_mortgage
            * rate
            * (1 + rate) ** total_payments
            / ((1 + rate) ** total_payments - 1)
        )
    total_interest = payment_amount * total_payments - total_mortgage

    return MortgageEstimate(
        purchase_price=purchase_price,
        down_payment=down_payment,
        minimum_down_payment=minimum,
        base_mortgage=base_mortgage,
        insurance_premium=insurance_premium,
        insurance_tax=insurance_tax,
        total_mortgage=total_mortgage,
        payment_amount=payment_amount,
        payment_frequency=payment_frequency,
        total_payments=total_payments,
        total_interest=total_interest,
    )
