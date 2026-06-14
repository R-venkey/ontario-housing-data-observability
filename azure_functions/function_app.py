"""Azure Functions entry points for live housing-data ingestion."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import azure.functions as func
from shared.bank_of_canada import (
    SOURCE_NAME,
    SOURCE_URL,
    fetch_raw_response,
    parse_mortgage_rates,
)
from shared.blob_store import build_blob_path, upload_raw_response
from shared.repository import (
    apply_schema,
    complete_pipeline_run,
    connect,
    ensure_source,
    fail_pipeline_run,
    latest_source_health,
    start_pipeline_run,
    upsert_mortgage_rates,
)


app = func.FunctionApp()
LOGGER = logging.getLogger("housing_ingestion")


def required_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value


@app.timer_trigger(
    schedule="0 15 8 * * *",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def ingest_bank_of_canada_rates(timer: func.TimerRequest) -> None:
    """Archive and persist the latest Bank of Canada mortgage rates daily."""
    del timer
    required_setting("PGHOST")
    required_setting("PGDATABASE")
    required_setting("PGUSER")
    required_setting("PGPASSWORD")
    storage_connection = required_setting("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("BRONZE_CONTAINER", "bronze")
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    source_id: int | None = None

    schema_path = Path(__file__).resolve().parent / "schema.sql"
    apply_schema(schema_path)

    try:
        with connect() as connection:
            source_id = ensure_source(
                connection,
                source_name=SOURCE_NAME,
                base_url=SOURCE_URL,
                expected_frequency="monthly",
                freshness_threshold_hours=1_080,
            )
            start_pipeline_run(
                connection,
                run_id=run_id,
                source_id=source_id,
                started_at=started_at,
                code_version=os.getenv("GIT_COMMIT_SHA", "unknown"),
            )

        raw_response = fetch_raw_response()
        records = parse_mortgage_rates(raw_response)
        blob_path = build_blob_path(SOURCE_NAME, run_id, started_at)
        upload_raw_response(
            connection_string=storage_connection,
            container_name=container_name,
            blob_path=blob_path,
            content=raw_response,
        )

        with connect() as connection:
            written = upsert_mortgage_rates(
                connection,
                source_id=source_id,
                run_id=run_id,
                records=records,
            )
            complete_pipeline_run(
                connection,
                run_id=run_id,
                completed_at=datetime.now(timezone.utc),
                records_read=len(records),
                records_written=written,
                source_watermark=max(record.observation_date for record in records),
                raw_object_path=blob_path,
            )
        LOGGER.info(
            "bank_of_canada_ingestion_succeeded",
            extra={"run_id": run_id, "records_written": written},
        )
    except Exception as error:
        if source_id is not None:
            fail_pipeline_run(
                run_id=run_id,
                completed_at=datetime.now(timezone.utc),
                error_message=str(error),
            )
        LOGGER.exception(
            "bank_of_canada_ingestion_failed",
            extra={"run_id": run_id},
        )
        raise


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(request: func.HttpRequest) -> func.HttpResponse:
    """Expose the latest persisted source status for external monitoring."""
    del request
    try:
        required_setting("PGHOST")
        health_data = latest_source_health()
        source_states = [
            source.get("status") == "success" and source.get("is_fresh")
            for source in health_data["sources"]
        ]
        overall_status = (
            "healthy"
            if source_states and all(source_states)
            else "degraded"
        )
        body = {"status": overall_status, **health_data}
        return func.HttpResponse(
            json.dumps(body, default=str),
            status_code=200 if overall_status == "healthy" else 503,
            mimetype="application/json",
        )
    except Exception as error:
        return func.HttpResponse(
            json.dumps({"status": "unhealthy", "error": str(error)}),
            status_code=503,
            mimetype="application/json",
        )
