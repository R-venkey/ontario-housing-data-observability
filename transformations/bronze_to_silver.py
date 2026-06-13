"""Clean bronze housing CSV data and write a typed silver Parquet dataset."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "bronze" / "ontario_housing_raw.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "silver" / "ontario_housing_clean.parquet"

CITY_NAMES = {
    "toronto": "Toronto",
    "oshawa": "Oshawa",
    "mississauga": "Mississauga",
    "ottawa": "Ottawa",
    "hamilton": "Hamilton",
    "brampton": "Brampton",
}
NUMERIC_COLUMNS = ("sale_price", "bedrooms", "days_on_market")
REQUIRED_COLUMNS = {
    "record_id",
    "city",
    "sale_date",
    "property_type",
    *NUMERIC_COLUMNS,
}


def clean_housing_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Standardize schema, types, city names, and duplicate records."""
    missing_columns = REQUIRED_COLUMNS.difference(raw_data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Input data is missing required columns: {missing}")

    clean = raw_data.copy()
    normalized_city = clean["city"].astype("string").str.strip().str.lower()
    clean["city"] = normalized_city.map(CITY_NAMES).fillna(
        normalized_city.str.title()
    )
    clean["property_type"] = clean["property_type"].astype("string").str.strip().str.title()
    clean["sale_date"] = pd.to_datetime(clean["sale_date"], errors="coerce")

    for column in NUMERIC_COLUMNS:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")

    clean = clean.drop_duplicates(subset=["record_id"], keep="last")
    clean = clean.drop_duplicates()
    clean = clean.sort_values(["sale_date", "city", "record_id"]).reset_index(drop=True)
    return clean


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input file does not exist: {args.input}")

    raw_data = pd.read_csv(args.input)
    clean_data = clean_housing_data(raw_data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    clean_data.to_parquet(args.output, index=False)
    print(f"Wrote {len(clean_data):,} clean records to {args.output}")


if __name__ == "__main__":
    main()
