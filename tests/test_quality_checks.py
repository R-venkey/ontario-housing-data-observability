import pandas as pd

from observability.quality_checks import find_missing_months, run_quality_checks


def valid_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "record_id": ["ON-1", "ON-2", "ON-3"],
            "city": ["Toronto", "Toronto", "Toronto"],
            "sale_date": ["2024-01-15", "2024-02-15", "2024-03-15"],
            "property_type": ["Condo", "Detached", "Townhouse"],
            "sale_price": [700_000, 1_200_000, 850_000],
            "bedrooms": [1, 4, 3],
            "days_on_market": [14, 21, 18],
        }
    )


def test_valid_data_receives_full_quality_score() -> None:
    report = run_quality_checks(valid_data())

    assert report["quality_score"] == 100.0
    assert all(report["checks"].values())


def test_duplicate_and_invalid_price_reduce_quality_score() -> None:
    data = valid_data()
    data.loc[2, "record_id"] = "ON-2"
    data.loc[1, "sale_price"] = -1

    report = run_quality_checks(data)

    assert report["details"]["duplicate_record_count"] == 1
    assert report["details"]["invalid_price_count"] == 1
    assert report["quality_score"] == 50.0


def test_missing_month_is_reported_by_city() -> None:
    data = valid_data().drop(index=1)

    missing = find_missing_months(data)

    assert missing == {"Toronto": ["2024-02"]}
