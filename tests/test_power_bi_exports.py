from pathlib import Path

import pandas as pd

from dashboard.power_bi_exports import (
    build_quality_checks_table,
    export_power_bi_files,
)


def sample_quality_report() -> dict:
    return {
        "row_count": 2,
        "quality_score": 100.0,
        "checks": {
            "required_values_complete": True,
            "record_ids_unique": True,
            "prices_valid": True,
            "monthly_coverage_complete": True,
        },
        "details": {
            "null_count": 0,
            "duplicate_record_count": 0,
            "invalid_price_count": 0,
            "missing_month_count": 0,
        },
    }


def test_quality_report_is_flattened_to_one_row_per_check() -> None:
    quality_table = build_quality_checks_table(sample_quality_report())

    assert len(quality_table) == 4
    assert quality_table["passed"].all()
    assert set(quality_table["observed_issue_count"]) == {0}


def test_power_bi_exports_have_stable_files_and_iso_dates(tmp_path: Path) -> None:
    silver = pd.DataFrame(
        {
            "record_id": ["ON-1"],
            "city": ["Toronto"],
            "sale_date": [pd.Timestamp("2025-01-15")],
            "property_type": ["Condo"],
            "sale_price": [700_000.0],
            "bedrooms": [2],
            "days_on_market": [14],
        }
    )
    gold = pd.DataFrame(
        {
            "city": ["Toronto"],
            "month": [pd.Timestamp("2025-01-01")],
            "average_price": [700_000.0],
            "median_price": [700_000.0],
            "sales_volume": [1],
            "average_days_on_market": [14.0],
            "average_bedrooms": [2.0],
        }
    )
    anomalies = pd.DataFrame(
        {
            "city": ["Toronto"],
            "month": [pd.Timestamp("2025-01-01")],
            "metric": ["sales_volume"],
            "current_value": [1.0],
            "mom_change_percent": [25.0],
        }
    )

    exports = export_power_bi_files(
        silver,
        gold,
        sample_quality_report(),
        anomalies,
        tmp_path,
    )

    assert set(exports) == {
        "transactions",
        "monthly_kpis",
        "quality_checks",
        "anomalies",
    }
    assert all(path.exists() for path in exports.values())
    assert (
        pd.read_csv(exports["transactions"]).loc[0, "sale_date"] == "2025-01-15"
    )
    assert pd.read_csv(exports["monthly_kpis"]).loc[0, "month"] == "2025-01-01"
