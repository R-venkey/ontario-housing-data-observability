"""Shared data loading and local pipeline bootstrapping for dashboard tools."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ingestion.sample_data_generator import generate_sample_data
from observability.anomaly_detection import detect_anomalies
from observability.quality_checks import run_quality_checks
from transformations.bronze_to_silver import clean_housing_data
from transformations.silver_to_gold import create_monthly_kpis


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRONZE_PATH = PROJECT_ROOT / "data" / "bronze" / "ontario_housing_raw.csv"
SILVER_PATH = PROJECT_ROOT / "data" / "silver" / "ontario_housing_clean.parquet"
GOLD_PATH = PROJECT_ROOT / "data" / "gold" / "monthly_city_kpis.parquet"
QUALITY_PATH = PROJECT_ROOT / "data" / "gold" / "quality_report.json"
ANOMALY_PATH = PROJECT_ROOT / "data" / "gold" / "anomaly_report.csv"


def ensure_pipeline_outputs() -> None:
    """Create all local pipeline outputs when one or more are missing."""
    required_paths = (
        BRONZE_PATH,
        SILVER_PATH,
        GOLD_PATH,
        QUALITY_PATH,
        ANOMALY_PATH,
    )
    if all(path.exists() for path in required_paths):
        return

    raw = generate_sample_data()
    clean = clean_housing_data(raw)
    gold = create_monthly_kpis(clean)
    quality = run_quality_checks(clean)
    anomalies = detect_anomalies(gold)

    for path in required_paths:
        path.parent.mkdir(parents=True, exist_ok=True)

    raw.to_csv(BRONZE_PATH, index=False)
    clean.to_parquet(SILVER_PATH, index=False)
    gold.to_parquet(GOLD_PATH, index=False)
    QUALITY_PATH.write_text(json.dumps(quality, indent=2), encoding="utf-8")
    anomalies.to_csv(ANOMALY_PATH, index=False)


def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame]:
    """Load typed silver, gold, quality, and anomaly datasets."""
    ensure_pipeline_outputs()
    silver = pd.read_parquet(SILVER_PATH)
    gold = pd.read_parquet(GOLD_PATH)
    quality = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
    anomalies = pd.read_csv(ANOMALY_PATH, parse_dates=["month"])
    silver["sale_date"] = pd.to_datetime(silver["sale_date"])
    gold["month"] = pd.to_datetime(gold["month"])
    return silver, gold, quality, anomalies
