-- ============================================
-- Migración: tabla permanente de récords históricos (weather_records)
-- ============================================
-- Crea la tabla weather_records (sin política de retención) y realiza el
-- backfill idempotente a partir de los datos existentes en weather_data
-- usando la zona horaria Europe/Madrid.

BEGIN;

CREATE TABLE IF NOT EXISTS weather_records (
    period_type   TEXT             NOT NULL CHECK (period_type IN ('daily', 'weekly', 'monthly', 'yearly', 'all_time')),
    period_key    TEXT             NOT NULL,
    metric        TEXT             NOT NULL,
    stat_type     TEXT             NOT NULL CHECK (stat_type IN ('min', 'max', 'sum')),
    value         DOUBLE PRECISION NOT NULL,
    recorded_at   TIMESTAMPTZ      NOT NULL,
    updated_at    TIMESTAMPTZ      NOT NULL DEFAULT NOW(),
    PRIMARY KEY (period_type, period_key, metric, stat_type)
);

CREATE INDEX IF NOT EXISTS idx_weather_records_lookup
    ON weather_records (period_type, period_key DESC);

WITH base_metrics AS (
    SELECT
        wd.time AS recorded_at,
        (wd.time AT TIME ZONE 'Europe/Madrid') AS local_time,
        m.metric,
        m.val
    FROM weather_data wd
    CROSS JOIN LATERAL (
        VALUES
            ('temperature', wd.temperature),
            ('humidity', wd.humidity),
            ('pressure', wd.pressure),
            ('wind_speed', wd.wind_speed),
            ('wind_gust', wd.wind_gust),
            ('rain', wd.rain),
            ('uv_index', wd.uv_index),
            ('illuminance', wd.illuminance)
    ) AS m(metric, val)
    WHERE m.val IS NOT NULL
),
scoped AS (
    SELECT
        p.period_type,
        p.period_key,
        b.metric,
        b.val,
        b.recorded_at
    FROM base_metrics b
    CROSS JOIN LATERAL (
        VALUES
            ('daily', to_char(b.local_time, 'YYYY-MM-DD')),
            ('weekly', to_char(b.local_time, 'IYYY-"W"IW')),
            ('monthly', to_char(b.local_time, 'YYYY-MM')),
            ('yearly', to_char(b.local_time, 'YYYY')),
            ('all_time', 'all')
    ) AS p(period_type, period_key)
),
max_records AS (
    SELECT DISTINCT ON (period_type, period_key, metric)
        period_type,
        period_key,
        metric,
        'max'::TEXT AS stat_type,
        val AS value,
        recorded_at
    FROM scoped
    ORDER BY period_type, period_key, metric, val DESC, recorded_at ASC
),
min_records AS (
    SELECT DISTINCT ON (period_type, period_key, metric)
        period_type,
        period_key,
        metric,
        'min'::TEXT AS stat_type,
        val AS value,
        recorded_at
    FROM scoped
    WHERE metric IN ('temperature', 'humidity', 'pressure')
    ORDER BY period_type, period_key, metric, val ASC, recorded_at ASC
),
sum_records AS (
    SELECT
        period_type,
        period_key,
        metric,
        'sum'::TEXT AS stat_type,
        SUM(val) AS value,
        COALESCE(MAX(recorded_at) FILTER (WHERE val > 0), MAX(recorded_at)) AS recorded_at
    FROM scoped
    WHERE metric = 'rain'
    GROUP BY period_type, period_key, metric
),
combined AS (
    SELECT * FROM max_records
    UNION ALL
    SELECT * FROM min_records
    UNION ALL
    SELECT * FROM sum_records
)
INSERT INTO weather_records (period_type, period_key, metric, stat_type, value, recorded_at)
SELECT period_type, period_key, metric, stat_type, value, recorded_at
FROM combined
ON CONFLICT (period_type, period_key, metric, stat_type) DO UPDATE
SET
    value = CASE
        WHEN weather_records.stat_type = 'max' THEN GREATEST(weather_records.value, EXCLUDED.value)
        WHEN weather_records.stat_type = 'min' THEN LEAST(weather_records.value, EXCLUDED.value)
        ELSE GREATEST(weather_records.value, EXCLUDED.value)
    END,
    recorded_at = CASE
        WHEN weather_records.stat_type = 'max' AND EXCLUDED.value > weather_records.value THEN EXCLUDED.recorded_at
        WHEN weather_records.stat_type = 'min' AND EXCLUDED.value < weather_records.value THEN EXCLUDED.recorded_at
        WHEN weather_records.stat_type = 'sum' AND EXCLUDED.value > weather_records.value THEN EXCLUDED.recorded_at
        ELSE weather_records.recorded_at
    END,
    updated_at = NOW();

COMMIT;
