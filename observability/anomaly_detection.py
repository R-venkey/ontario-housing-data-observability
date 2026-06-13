"""Detect material month-over-month changes in housing market KPIs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "gold" / "monthly_city_kpis.parquet"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "gold" / "anomaly_report.csv"
MONITORED_METRICS = ("average_price", "sales_volume")


def detect_anomalies(
    monthly_kpis: pd.DataFrame,
    threshold: float = 0.20,
) -> pd.DataFrame:
    """Flag metric changes whose absolute month-over-month rate exceeds threshold."""
    if threshold < 0:
        raise ValueError("threshold must be non-negative")

    data = monthly_kpis.copy()
    data["month"] = pd.to_datetime(data["month"], errors="coerce")
    data = data.sort_values(["city", "month"]).reset_index(drop=True)
    anomaly_frames: list[pd.DataFrame] = []

    for metric in MONITORED_METRICS:
        change_column = f"{metric}_mom_change"
        data[change_column] = data.groupby("city")[metric].pct_change()
        flagged = data.loc[
            data[change_column].abs() > threshold,
            ["city", "month", metric, change_column],
        ].copy()
        flagged = flagged.rename(
            columns={metric: "current_value", change_column: "mom_change"}
        )
        flagged["metric"] = metric
        anomaly_frames.append(flagged)

    if not anomaly_frames:
        return pd.DataFrame(
            columns=["city", "month", "metric", "current_value", "mom_change"]
        )

    anomalies = pd.concat(anomaly_frames, ignore_index=True)
    anomalies["mom_change_percent"] = (anomalies.pop("mom_change") * 100).round(2)
    return anomalies[
        ["city", "month", "metric", "current_value", "mom_change_percent"]
    ].sort_values(["month", "city", "metric"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.20,
        help="Decimal month-over-month threshold; default is 0.20 (20%%).",
    )
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input file does not exist: {args.input}")

    monthly_kpis = pd.read_parquet(args.input)
    anomalies = detect_anomalies(monthly_kpis, args.threshold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    anomalies.to_csv(args.output, index=False)
    print(f"Detected {len(anomalies):,} anomalies above {args.threshold:.0%}")
    print(f"Wrote anomaly report to {args.output}")


if __name__ == "__main__":
    main()
