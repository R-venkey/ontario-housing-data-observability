"""Generate deterministic synthetic Ontario housing transaction data."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "bronze" / "ontario_housing_raw.csv"

CITY_PROFILES = {
    "Toronto": {"base_price": 1_100_000, "monthly_sales": 90},
    "Oshawa": {"base_price": 720_000, "monthly_sales": 42},
    "Mississauga": {"base_price": 980_000, "monthly_sales": 60},
    "Ottawa": {"base_price": 760_000, "monthly_sales": 65},
    "Hamilton": {"base_price": 790_000, "monthly_sales": 52},
    "Brampton": {"base_price": 940_000, "monthly_sales": 58},
}

PROPERTY_TYPES = ("Detached", "Semi-Detached", "Townhouse", "Condo")
PROPERTY_MULTIPLIERS = {
    "Detached": 1.18,
    "Semi-Detached": 1.02,
    "Townhouse": 0.88,
    "Condo": 0.68,
}


def generate_sample_data(
    start_date: str = "2024-01-01",
    months: int = 24,
    seed: int = 42,
) -> pd.DataFrame:
    """Create transaction-level housing records for configured Ontario cities."""
    rng = np.random.default_rng(seed)
    month_starts = pd.date_range(start=start_date, periods=months, freq="MS")
    records: list[dict[str, object]] = []
    record_number = 1

    for month_index, month_start in enumerate(month_starts):
        seasonal_factor = 1 + 0.08 * np.sin((month_start.month - 3) / 12 * 2 * np.pi)
        trend_factor = 1 + 0.003 * month_index

        for city, profile in CITY_PROFILES.items():
            expected_sales = profile["monthly_sales"] * seasonal_factor
            sales_count = max(10, int(rng.normal(expected_sales, expected_sales * 0.08)))

            for _ in range(sales_count):
                property_type = str(rng.choice(PROPERTY_TYPES, p=[0.4, 0.18, 0.22, 0.2]))
                days_in_month = int(month_start.days_in_month)
                sale_date = month_start + pd.Timedelta(days=int(rng.integers(0, days_in_month)))
                price_noise = float(rng.lognormal(mean=0, sigma=0.12))
                sale_price = (
                    profile["base_price"]
                    * PROPERTY_MULTIPLIERS[property_type]
                    * trend_factor
                    * price_noise
                )

                records.append(
                    {
                        "record_id": f"ON-{record_number:07d}",
                        "city": city,
                        "sale_date": sale_date.strftime("%Y-%m-%d"),
                        "property_type": property_type,
                        "sale_price": round(sale_price, 2),
                        "bedrooms": int(rng.integers(1, 6)),
                        "days_on_market": max(1, int(rng.normal(24, 9))),
                    }
                )
                record_number += 1

    return pd.DataFrame.from_records(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.months <= 0:
        parser.error("--months must be greater than zero")

    data = generate_sample_data(args.start_date, args.months, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.output, index=False)
    print(f"Wrote {len(data):,} raw records to {args.output}")


if __name__ == "__main__":
    main()
