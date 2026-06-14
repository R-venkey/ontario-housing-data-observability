"""PostgreSQL persistence for pipeline runs and mortgage rates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable

from .bank_of_canada import MortgageRateRecord


def connect():
    """Connect using PostgreSQL's standard PGHOST/PGUSER environment settings."""
    import psycopg

    return psycopg.connect()


def apply_schema(schema_path: Path) -> None:
    """Apply the idempotent project schema."""
    statements = schema_path.read_text(encoding="utf-8")
    with connect() as connection:
        connection.execute(statements)


def ensure_source(
    connection,
    *,
    source_name: str,
    base_url: str,
    expected_frequency: str,
    freshness_threshold_hours: int,
) -> int:
    """Create or update a source definition and return its identifier."""
    row = connection.execute(
        """
        INSERT INTO source_systems (
            source_name, base_url, expected_frequency, freshness_threshold_hours
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (source_name) DO UPDATE SET
            base_url = EXCLUDED.base_url,
            expected_frequency = EXCLUDED.expected_frequency,
            freshness_threshold_hours = EXCLUDED.freshness_threshold_hours
        RETURNING source_id
        """,
        (
            source_name,
            base_url,
            expected_frequency,
            freshness_threshold_hours,
        ),
    ).fetchone()
    return int(row[0])


def start_pipeline_run(
    connection,
    *,
    run_id: str,
    source_id: int,
    started_at: datetime,
    code_version: str,
) -> None:
    connection.execute(
        """
        INSERT INTO pipeline_runs (
            run_id, source_id, started_at, status, code_version
        )
        VALUES (%s, %s, %s, 'running', %s)
        """,
        (run_id, source_id, started_at, code_version),
    )


def upsert_mortgage_rates(
    connection,
    *,
    source_id: int,
    run_id: str,
    records: Iterable[MortgageRateRecord],
) -> int:
    """Upsert normalized observations and return the written row count."""
    rows = [
        (
            record.series_id,
            record.observation_date,
            record.label,
            record.description,
            record.rate_percent,
            source_id,
            run_id,
        )
        for record in records
    ]
    connection.executemany(
        """
        INSERT INTO mortgage_rates (
            series_id, observation_date, label, description, rate_percent,
            source_id, run_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (series_id, observation_date) DO UPDATE SET
            label = EXCLUDED.label,
            description = EXCLUDED.description,
            rate_percent = EXCLUDED.rate_percent,
            source_id = EXCLUDED.source_id,
            run_id = EXCLUDED.run_id,
            ingested_at = NOW()
        """,
        rows,
    )
    return len(rows)


def complete_pipeline_run(
    connection,
    *,
    run_id: str,
    completed_at: datetime,
    records_read: int,
    records_written: int,
    source_watermark,
    raw_object_path: str,
) -> None:
    connection.execute(
        """
        UPDATE pipeline_runs
        SET completed_at = %s,
            status = 'success',
            records_read = %s,
            records_written = %s,
            source_watermark = %s,
            raw_object_path = %s
        WHERE run_id = %s
        """,
        (
            completed_at,
            records_read,
            records_written,
            source_watermark,
            raw_object_path,
            run_id,
        ),
    )


def fail_pipeline_run(
    *,
    run_id: str,
    completed_at: datetime,
    error_message: str,
) -> None:
    """Mark a previously opened run failed using a fresh transaction."""
    with connect() as connection:
        connection.execute(
            """
            UPDATE pipeline_runs
            SET completed_at = %s,
                status = 'failed',
                error_message = %s
            WHERE run_id = %s
            """,
            (completed_at, error_message[:4000], run_id),
        )


def latest_source_health() -> dict:
    """Return the latest pipeline status and freshness for every source."""
    from psycopg.rows import dict_row

    with connect() as connection:
        connection.row_factory = dict_row
        rows = connection.execute(
            """
            SELECT DISTINCT ON (s.source_id)
                s.source_name,
                s.expected_frequency,
                s.freshness_threshold_hours,
                p.status,
                p.started_at,
                p.completed_at,
                p.source_watermark,
                p.records_written,
                p.error_message,
                CASE
                    WHEN p.completed_at IS NULL THEN FALSE
                    WHEN p.completed_at >= (
                        NOW() - make_interval(hours => s.freshness_threshold_hours)
                    ) THEN TRUE
                    ELSE FALSE
                END AS is_fresh
            FROM source_systems s
            LEFT JOIN pipeline_runs p ON p.source_id = s.source_id
            ORDER BY s.source_id, p.started_at DESC NULLS LAST
            """
        ).fetchall()
    return {"sources": rows}
