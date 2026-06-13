"""Export dashboard datasets as flat, Power BI-ready CSV files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.data_service import PROJECT_ROOT, load_dashboard_data


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "exports"


def build_quality_checks_table(quality: dict[str, Any]) -> pd.DataFrame:
    """Flatten the quality report into one row per control."""
    details = quality["details"]
    observed_counts = {
        "required_values_complete": details["null_count"],
        "record_ids_unique": details["duplicate_record_count"],
        "prices_valid": details["invalid_price_count"],
        "monthly_coverage_complete": details["missing_month_count"],
    }
    return pd.DataFrame(
        [
            {
                "check_name": check_name,
                "passed": passed,
                "observed_issue_count": observed_counts[check_name],
                "quality_score": quality["quality_score"],
                "evaluated_row_count": quality["row_count"],
            }
            for check_name, passed in quality["checks"].items()
        ]
    )


def build_export_tables(
    silver: pd.DataFrame,
    gold: pd.DataFrame,
    quality: dict[str, Any],
    anomalies: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build flat analytics tables with ISO-formatted dates."""
    transactions = silver.copy()
    transactions["sale_date"] = pd.to_datetime(
        transactions["sale_date"]
    ).dt.strftime("%Y-%m-%d")

    monthly_kpis = gold.copy()
    monthly_kpis["month"] = pd.to_datetime(monthly_kpis["month"]).dt.strftime(
        "%Y-%m-%d"
    )

    anomaly_export = anomalies.copy()
    anomaly_export["month"] = pd.to_datetime(anomaly_export["month"]).dt.strftime(
        "%Y-%m-%d"
    )

    return {
        "transactions": transactions,
        "monthly_kpis": monthly_kpis,
        "quality_checks": build_quality_checks_table(quality),
        "anomalies": anomaly_export,
    }


def dataframe_to_csv_bytes(data: pd.DataFrame) -> bytes:
    """Serialize a DataFrame as UTF-8 CSV for browser downloads."""
    return data.to_csv(index=False).encode("utf-8")


def export_power_bi_files(
    silver: pd.DataFrame,
    gold: pd.DataFrame,
    quality: dict[str, Any],
    anomalies: pd.DataFrame,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    """Write analytics tables with stable names and ISO-formatted dates."""
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = build_export_tables(silver, gold, quality, anomalies)

    exports = {
        "transactions": output_dir / "housing_transactions.csv",
        "monthly_kpis": output_dir / "monthly_city_kpis.csv",
        "quality_checks": output_dir / "quality_checks.csv",
        "anomalies": output_dir / "market_anomalies.csv",
    }
    for export_name, path in exports.items():
        tables[export_name].to_csv(path, index=False)
    return exports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    silver, gold, quality, anomalies = load_dashboard_data()
    exports = export_power_bi_files(
        silver,
        gold,
        quality,
        anomalies,
        args.output_dir,
    )
    for export_name, path in exports.items():
        print(f"Wrote {export_name}: {path}")


if __name__ == "__main__":
    main()
