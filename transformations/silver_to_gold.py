"""Aggregate silver housing transactions into monthly city KPIs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "silver" / "ontario_housing_clean.parquet"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "gold" / "monthly_city_kpis.parquet"


def create_monthly_kpis(silver_data: pd.DataFrame) -> pd.DataFrame:
    """Create monthly pricing, volume, and property KPIs by city."""
    data = silver_data.copy()
    data["sale_date"] = pd.to_datetime(data["sale_date"], errors="coerce")
    data = data.dropna(subset=["city", "sale_date", "sale_price"])
    data["month"] = data["sale_date"].dt.to_period("M").dt.to_timestamp()

    monthly = (
        data.groupby(["city", "month"], as_index=False)
        .agg(
            average_price=("sale_price", "mean"),
            median_price=("sale_price", "median"),
            sales_volume=("record_id", "nunique"),
            average_days_on_market=("days_on_market", "mean"),
            average_bedrooms=("bedrooms", "mean"),
        )
        .sort_values(["city", "month"])
        .reset_index(drop=True)
    )

    currency_columns = ["average_price", "median_price"]
    monthly[currency_columns] = monthly[currency_columns].round(2)
    monthly[["average_days_on_market", "average_bedrooms"]] = monthly[
        ["average_days_on_market", "average_bedrooms"]
    ].round(2)
    return monthly


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input file does not exist: {args.input}")

    silver_data = pd.read_parquet(args.input)
    gold_data = create_monthly_kpis(silver_data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    gold_data.to_parquet(args.output, index=False)
    print(f"Wrote {len(gold_data):,} monthly KPI rows to {args.output}")


if __name__ == "__main__":
    main()
