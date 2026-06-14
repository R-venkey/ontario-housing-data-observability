CREATE TABLE IF NOT EXISTS source_systems (
    source_id BIGSERIAL PRIMARY KEY,
    source_name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    expected_frequency TEXT NOT NULL,
    freshness_threshold_hours INTEGER NOT NULL CHECK (freshness_threshold_hours > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id UUID PRIMARY KEY,
    source_id BIGINT NOT NULL REFERENCES source_systems(source_id),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'warning', 'failed')),
    records_read INTEGER NOT NULL DEFAULT 0,
    records_written INTEGER NOT NULL DEFAULT 0,
    records_rejected INTEGER NOT NULL DEFAULT 0,
    retry_count INTEGER NOT NULL DEFAULT 0,
    source_watermark TIMESTAMPTZ,
    raw_object_path TEXT,
    code_version TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_source_started
    ON pipeline_runs (source_id, started_at DESC);

CREATE TABLE IF NOT EXISTS mortgage_rates (
    series_id TEXT NOT NULL,
    observation_date DATE NOT NULL,
    label TEXT NOT NULL,
    description TEXT,
    rate_percent NUMERIC(8, 4) NOT NULL,
    source_id BIGINT NOT NULL REFERENCES source_systems(source_id),
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (series_id, observation_date)
);

CREATE INDEX IF NOT EXISTS idx_mortgage_rates_observation_date
    ON mortgage_rates (observation_date DESC);

CREATE TABLE IF NOT EXISTS quality_check_runs (
    quality_result_id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id),
    check_name TEXT NOT NULL,
    dimension TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pass', 'warning', 'fail')),
    observed_value NUMERIC,
    threshold_value NUMERIC,
    details JSONB,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_check_runs_run_id
    ON quality_check_runs (run_id);
