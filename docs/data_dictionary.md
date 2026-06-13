# Data Dictionary

## Bronze: Raw Housing Transactions

File: `data/bronze/ontario_housing_raw.csv`

| Column | Type at ingestion | Description |
| --- | --- | --- |
| `record_id` | string | Synthetic unique transaction identifier. |
| `city` | string | Ontario city supplied by the source. |
| `sale_date` | string | Transaction date in `YYYY-MM-DD` format. |
| `property_type` | string | Detached, semi-detached, townhouse, or condo. |
| `sale_price` | numeric-like | Transaction sale price in Canadian dollars. |
| `bedrooms` | integer-like | Number of bedrooms. |
| `days_on_market` | integer-like | Days between listing and sale. |

The bronze layer preserves source-oriented values before standardization.

## Silver: Clean Housing Transactions

File: `data/silver/ontario_housing_clean.parquet`

| Column | Type | Description |
| --- | --- | --- |
| `record_id` | string | Deduplicated transaction identifier. |
| `city` | string | Trimmed and title-cased canonical city name. |
| `sale_date` | datetime | Parsed transaction date. Invalid values become null. |
| `property_type` | string | Trimmed and title-cased property category. |
| `sale_price` | float | Parsed sale price in Canadian dollars. |
| `bedrooms` | numeric | Parsed bedroom count. |
| `days_on_market` | numeric | Parsed market duration in days. |

Grain: one row per unique housing transaction.

## Gold: Monthly City KPIs

File: `data/gold/monthly_city_kpis.parquet`

| Column | Type | Description |
| --- | --- | --- |
| `city` | string | Canonical Ontario city name. |
| `month` | datetime | First calendar day of the reporting month. |
| `average_price` | float | Mean transaction price for the city-month. |
| `median_price` | float | Median transaction price for the city-month. |
| `sales_volume` | integer | Count of unique transaction identifiers. |
| `average_days_on_market` | float | Mean days on market for sold properties. |
| `average_bedrooms` | float | Mean bedroom count for sold properties. |

Grain: one row per city and calendar month.

## Quality Report

File: `data/gold/quality_report.json`

| Field | Type | Description |
| --- | --- | --- |
| `row_count` | integer | Silver rows evaluated. |
| `quality_score` | float | Percentage of quality controls that passed. |
| `checks.required_values_complete` | boolean | Required columns contain no nulls. |
| `checks.record_ids_unique` | boolean | No duplicate record identifiers exist. |
| `checks.prices_valid` | boolean | Prices are numeric, positive, and at most $20 million. |
| `checks.monthly_coverage_complete` | boolean | No month is missing within each city's observed range. |
| `details.null_count` | integer | Total null values in required columns. |
| `details.nulls_by_column` | object | Null counts for affected columns. |
| `details.duplicate_record_count` | integer | Duplicate record identifier count. |
| `details.invalid_price_count` | integer | Invalid or implausible price count. |
| `details.missing_month_count` | integer | Missing city-month count. |
| `details.missing_months_by_city` | object | Missing `YYYY-MM` periods grouped by city. |

## Anomaly Report

File: `data/gold/anomaly_report.csv`

| Column | Type | Description |
| --- | --- | --- |
| `city` | string | City where the change occurred. |
| `month` | datetime | Month containing the flagged value. |
| `metric` | string | `average_price` or `sales_volume`. |
| `current_value` | float | Metric value in the flagged month. |
| `mom_change_percent` | float | Month-over-month percentage change. |

A row is emitted when the absolute month-over-month change exceeds 20 percent.
An anomaly is an investigation signal, not automatically a data-quality defect.

## Power BI Exports

Directory: `data/exports/`

| File | Source | Recommended use |
| --- | --- | --- |
| `housing_transactions.csv` | Silver | Transaction detail, property mix, drill-through. |
| `monthly_city_kpis.csv` | Gold | Time-series visuals and city comparisons. |
| `quality_checks.csv` | Quality JSON | Quality scorecards and failed-control reporting. |
| `market_anomalies.csv` | Anomaly CSV | Exception tables and alert-focused visuals. |

Dates are exported as ISO `YYYY-MM-DD` strings. Column names are stable and use
snake case to support repeatable Power BI refreshes.
