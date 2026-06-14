from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from azure_functions.shared.bank_of_canada import parse_mortgage_rates
from azure_functions.shared.blob_store import build_blob_path


FIXTURE = Path(__file__).parent / "fixtures" / "bank_of_canada_rates.json"


def test_parse_mortgage_rates_normalizes_populated_observations():
    records = parse_mortgage_rates(FIXTURE.read_bytes())

    assert len(records) == 3
    assert records[0].series_id == "V80691335"
    assert records[0].rate_percent == Decimal("6.09")
    assert records[-1].observation_date.isoformat() == "2026-05-31"
    assert records[-1].label == "Conventional mortgage - 5-year"


def test_build_blob_path_partitions_raw_responses_by_utc_date():
    retrieved_at = datetime(2026, 6, 14, 10, 30, tzinfo=timezone.utc)

    path = build_blob_path("bank_of_canada_mortgage_rates", "run-123", retrieved_at)

    assert path == (
        "bank_of_canada_mortgage_rates/year=2026/month=06/"
        "day=14/run-123.json"
    )
