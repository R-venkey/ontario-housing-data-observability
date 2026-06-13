"""Run housing data quality checks and calculate an overall quality score."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "silver" / "ontario_housing_clean.parquet"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "gold" / "quality_report.json"
REQUIRED_COLUMNS = (
    "record_id",
    "city",
    "sale_date",
    "property_type",
    "sale_price",
    "bedrooms",
    "days_on_market",
)
MAX_REASONABLE_PRICE = 20_000_000


def find_missing_months(data: pd.DataFrame) -> dict[str, list[str]]:
    """Return missing YYYY-MM periods between each city's first and last record."""
    dated = data.copy()
    dated["sale_date"] = pd.to_datetime(dated["sale_date"], errors="coerce")
    dated = dated.dropna(subset=["city", "sale_date"])
    missing_by_city: dict[str, list[str]] = {}

    for city, city_data in dated.groupby("city"):
        observed = city_data["sale_date"].dt.to_period("M").unique()
        expected = pd.period_range(min(observed), max(observed), freq="M")
        missing = expected.difference(observed)
        if len(missing):
            missing_by_city[str(city)] = [str(period) for period in missing]

    return missing_by_city


def run_quality_checks(data: pd.DataFrame) -> dict[str, Any]:
    """Evaluate core quality dimensions and return a serializable report."""
    missing_columns = set(REQUIRED_COLUMNS).difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Data is missing required columns: {missing}")

    null_counts = data[list(REQUIRED_COLUMNS)].isna().sum()
    null_count = int(null_counts.sum())
    duplicate_count = int(data.duplicated(subset=["record_id"]).sum())
    prices = pd.to_numeric(data["sale_price"], errors="coerce")
    invalid_price_count = int(
        ((prices <= 0) | (prices > MAX_REASONABLE_PRICE) | prices.isna()).sum()
    )
    missing_months = find_missing_months(data)
    missing_month_count = sum(len(months) for months in missing_months.values())

    checks = {
        "required_values_complete": null_count == 0,
        "record_ids_unique": duplicate_count == 0,
        "prices_valid": invalid_price_count == 0,
        "monthly_coverage_complete": missing_month_count == 0,
    }
    quality_score = round(100 * sum(checks.values()) / len(checks), 2)

    return {
        "row_count": int(len(data)),
        "quality_score": quality_score,
        "checks": checks,
        "details": {
            "null_count": null_count,
            "nulls_by_column": {
                column: int(count)
                for column, count in null_counts.items()
                if count > 0
            },
            "duplicate_record_count": duplicate_count,
            "invalid_price_count": invalid_price_count,
            "missing_month_count": missing_month_count,
            "missing_months_by_city": missing_months,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input file does not exist: {args.input}")

    data = pd.read_parquet(args.input)
    report = run_quality_checks(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Quality score: {report['quality_score']:.2f}%")
    print(f"Wrote quality report to {args.output}")


if __name__ == "__main__":
    main()
