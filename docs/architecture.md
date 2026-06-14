# Architecture

## Overview

The Ontario Housing Data Quality & Observability Platform combines a local
medallion pipeline with a deployment-ready Azure ingestion path. Synthetic
transactions support reproducible analytics and modeling, while official Bank
of Canada mortgage rates establish the first live-data source.

```mermaid
flowchart LR
    BOC["Bank of Canada Valet API"] --> AF["Azure Function timer"]
    AF --> AB["Azure Blob Bronze JSON"]
    AF --> PG["Azure PostgreSQL"]
    AF --> AI["Application Insights"]
    PG --> HE["Function health endpoint"]
    HE --> MON["Azure Monitor availability alert"]
    PG -. "next dashboard integration" .-> K
    A["Synthetic Ontario housing generator"] --> B["Bronze CSV"]
    B --> C["Schema and type cleaning"]
    C --> D["Silver Parquet"]
    D --> E["Monthly KPI aggregation"]
    D --> F["Quality controls"]
    E --> G["Gold Parquet"]
    G --> H["Anomaly detection"]
    F --> I["Quality JSON"]
    H --> J["Anomaly CSV"]
    D --> K["Streamlit dashboard"]
    G --> K
    I --> K
    J --> K
    D --> L["Power BI CSV exports"]
    G --> L
    I --> L
    J --> L
    D --> M["Price model training"]
    M --> K
```

## Cloud Data Flow

The Azure Function runs daily at 08:15 UTC. It downloads the official mortgage
rate response, writes an immutable date-partitioned copy to Blob Storage, and
upserts normalized observations into PostgreSQL. Every attempt creates a
`pipeline_runs` record with timestamps, row counts, source watermark, raw
object path, code version, and any error message.

The anonymous `/api/health` endpoint reports the latest status and freshness of
each source. Application Insights captures invocations and exceptions; Azure
Monitor can poll the endpoint and alert when it returns `503`.

Infrastructure is defined in `infra/main.bicep`. The initial footprint uses a
Functions Consumption plan, Standard LRS Blob Storage, Log Analytics,
Application Insights, and PostgreSQL Flexible Server B1ms with 32 GB storage.

## Components

### Ingestion

`ingestion/sample_data_generator.py` creates deterministic transaction-level
records for Toronto, Oshawa, Mississauga, Ottawa, Hamilton, and Brampton. City
profiles, seasonality, property types, and seeded random variation make the
dataset reproducible while preserving realistic differences between markets.

### Bronze Layer

`data/bronze/ontario_housing_raw.csv` is the immutable landing representation.
It preserves the source-oriented string formats that a production ingestion
job would receive. Generated data is intentionally excluded from Git.

### Silver Layer

`transformations/bronze_to_silver.py`:

1. Validates required columns.
2. Trims and standardizes city and property-type values.
3. Parses sale dates.
4. Coerces price, bedroom, and days-on-market fields to numeric types.
5. Removes duplicate record identifiers and duplicate rows.
6. Sorts the result and writes Parquet.

The silver dataset is the trusted transaction-level source for downstream
quality analysis and reporting.

### Gold Layer

`transformations/silver_to_gold.py` groups valid transactions by city and month.
It publishes average price, median price, sales volume, average days on market,
and average bedrooms as analytics-ready Parquet.

### Observability

`observability/quality_checks.py` evaluates completeness, uniqueness, price
validity, and monthly coverage. The report includes issue counts and a quality
score based on the percentage of controls that pass.

`observability/anomaly_detection.py` calculates month-over-month changes in
average price and sales volume. Absolute changes greater than 20 percent are
written to the anomaly report for investigation.

### Presentation and Export

`dashboard/app.py` provides interactive city and date filters, market KPI cards,
trend charts, quality status, anomaly visualization, and recent transactions.
`dashboard/data_service.py` generates missing local outputs and provides one
typed loading interface for presentation tools.

`dashboard/power_bi_exports.py` flattens the silver, gold, quality, and anomaly
outputs into stable CSV files under `data/exports/`. These files can be loaded
directly with Power BI's Folder or Text/CSV connectors.

### Predictive Model

`modeling/price_model.py` trains a random-forest regression pipeline using city,
property type, bedrooms, days on market, sale year, and sale month. Categorical
features are one-hot encoded inside the model pipeline. A held-out test split
produces mean absolute error and R-squared metrics, while the 80th percentile of
absolute test errors defines the displayed estimate range.

The dashboard accepts a street address for display context only. The address is
not geocoded, stored, or used as a feature because the synthetic source data has
no street, postal-code, latitude, or longitude fields.

`modeling/mortgage.py` converts the model estimate into an editable Canadian
mortgage scenario. It validates federal minimum down-payment tiers, estimates
standard CMHC premiums by loan-to-value, applies Ontario sales tax to the
insurance premium, and converts nominal semi-annual interest into monthly,
bi-weekly, or weekly payment rates.

## Execution Flow

```text
sample_data_generator.py
    -> bronze_to_silver.py
    -> silver_to_gold.py
    -> quality_checks.py
    -> anomaly_detection.py
    -> Streamlit or Power BI exports
```

The dashboard can bootstrap this flow when outputs are absent. Explicit script
execution remains the preferred pattern for scheduled or production workloads.

## Storage and Version Control

Code, tests, configuration, documentation, and empty layer markers are tracked.
Generated CSV, Parquet, and JSON artifacts are ignored to keep the repository
small, reproducible, and free from derived data.

## Testing and CI

Pytest covers quality rules and Power BI export contracts. GitHub Actions runs
the suite with Python 3.11 on pushes to `main` and on pull requests. The
workflow also compiles Python sources before testing to catch syntax errors.

## Production Evolution

The next source adapters will target municipal permits, Statistics Canada, and
CMHC housing supply data. PostgreSQL read models can then replace selected
synthetic dashboard inputs while retaining local files as a demo fallback.
Later hardening includes Key Vault references, managed identity, restricted
networking, schema-specific database roles, and persisted quality trends.
