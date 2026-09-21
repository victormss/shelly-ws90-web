-- ============================================
-- Weather Station — Database Initialization
-- ============================================
-- Este script se ejecuta automáticamente al crear el contenedor TimescaleDB

-- Activar la extensión TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Tabla principal de datos meteorológicos
CREATE TABLE IF NOT EXISTS weather_data (
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    temperature     DOUBLE PRECISION,
    humidity        DOUBLE PRECISION,
    pressure        DOUBLE PRECISION,
    wind_speed      DOUBLE PRECISION,
    wind_direction  DOUBLE PRECISION,
    wind_gust       DOUBLE PRECISION,
    rain            DOUBLE PRECISION,
    uv_index        DOUBLE PRECISION,
    illuminance     DOUBLE PRECISION
);

-- Convertir a hypertable de TimescaleDB (optimizado para series temporales)
SELECT create_hypertable('weather_data', 'time', if_not_exists => TRUE);

-- Índice para consultas por rango de tiempo (ya incluido en hypertable, pero explícito)
CREATE INDEX IF NOT EXISTS idx_weather_time ON weather_data (time DESC);

-- Política de retención automática: mantener 1 año de datos
SELECT add_retention_policy('weather_data', INTERVAL '1 year', if_not_exists => TRUE);

-- Vista materializada continua: estadísticas por hora
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_weather_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    AVG(temperature)    AS avg_temp,
    MIN(temperature)    AS min_temp,
    MAX(temperature)    AS max_temp,
    AVG(humidity)       AS avg_humidity,
    MIN(humidity)       AS min_humidity,
    MAX(humidity)       AS max_humidity,
    AVG(pressure)       AS avg_pressure,
    AVG(wind_speed)     AS avg_wind_speed,
    MAX(wind_speed)     AS max_wind_speed,
    MAX(wind_gust)      AS max_wind_gust,
    SUM(rain)           AS total_rain,
    MAX(uv_index)       AS max_uv_index,
    AVG(illuminance)    AS avg_illuminance,
    COUNT(*)            AS sample_count
FROM weather_data
GROUP BY bucket
WITH NO DATA;

-- Vista materializada continua: estadísticas diarias
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_weather_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    AVG(temperature)    AS avg_temp,
    MIN(temperature)    AS min_temp,
    MAX(temperature)    AS max_temp,
    AVG(humidity)       AS avg_humidity,
    MIN(humidity)       AS min_humidity,
    MAX(humidity)       AS max_humidity,
    AVG(pressure)       AS avg_pressure,
    AVG(wind_speed)     AS avg_wind_speed,
    MAX(wind_speed)     AS max_wind_speed,
    MAX(wind_gust)      AS max_wind_gust,
    SUM(rain)           AS total_rain,
    MAX(uv_index)       AS max_uv_index,
    AVG(illuminance)    AS avg_illuminance,
    COUNT(*)            AS sample_count
FROM weather_data
GROUP BY bucket
WITH NO DATA;

-- Políticas de refresco automático para las vistas materializadas
SELECT add_continuous_aggregate_policy('hourly_weather_stats',
    start_offset    => INTERVAL '3 hours',
    end_offset      => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists   => TRUE
);

SELECT add_continuous_aggregate_policy('daily_weather_stats',
    start_offset    => INTERVAL '3 days',
    end_offset      => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists   => TRUE
);
