"""Bank of Canada Valet mortgage-rate ingestion."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from urllib.request import urlopen


SOURCE_NAME = "bank_of_canada_mortgage_rates"
SOURCE_URL = (
    "https://www.bankofcanada.ca/valet/observations/group/"
    "A4_RATES_MORTGAGES/json?recent=2"
)


@dataclass(frozen=True)
class MortgageRateRecord:
    series_id: str
    observation_date: date
    label: str
    description: str
    rate_percent: Decimal


def fetch_raw_response(timeout_seconds: int = 30) -> bytes:
    """Download the latest mortgage-rate observations."""
    with urlopen(SOURCE_URL, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise RuntimeError(f"Bank of Canada returned HTTP {response.status}")
        return response.read()


def parse_mortgage_rates(raw_response: bytes) -> list[MortgageRateRecord]:
    """Normalize all populated series observations in a Valet response."""
    payload: dict[str, Any] = json.loads(raw_response)
    observations = payload.get("observations", [])
    series_details = payload.get("seriesDetail", {})
    records: list[MortgageRateRecord] = []

    for observation in observations:
        observation_date = date.fromisoformat(observation["d"])
        for series_id, value in observation.items():
            if series_id == "d" or not value or value.get("v") in (None, ""):
                continue
            details = series_details.get(series_id, {})
            records.append(
                MortgageRateRecord(
                    series_id=series_id,
                    observation_date=observation_date,
                    label=details.get("label", series_id),
                    description=details.get("description", ""),
                    rate_percent=Decimal(str(value["v"])),
                )
            )

    if not records:
        raise ValueError("Bank of Canada response contained no mortgage rates")
    return records
