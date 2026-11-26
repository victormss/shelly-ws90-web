"""Weather Station API — Public weather data endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Literal, Optional
from datetime import datetime, timezone, timedelta

from app.config import get_settings
from app.database import get_db
from app.schemas import (
    WeatherResponse,
    WeatherStatsResponse,
    WeatherPeriodRecordsResponse,
    WeatherRecordsSummaryResponse,
)
from app.services.records import (
    PERIOD_TYPES,
    compute_period_keys,
    rows_to_record_dict,
)

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get(
    "/current",
    response_model=WeatherResponse | None,
    summary="Get current weather data",
    description="Returns the most recent weather data point.",
)
async def get_current_weather(
    db: AsyncSession = Depends(get_db),
) -> WeatherResponse | None:
    """Return the latest weather data point."""
    result = await db.execute(
        text("""
            SELECT time, temperature, humidity, pressure,
                   wind_speed, wind_direction, wind_gust,
                   rain, uv_index, illuminance
            FROM weather_data
            ORDER BY time DESC
            LIMIT 1
        """)
    )
    row = result.fetchone()

    if row is None:
        return None

    return WeatherResponse(
        time=row.time,
        temperature=row.temperature,
        humidity=row.humidity,
        pressure=row.pressure,
        wind_speed=row.wind_speed,
        wind_direction=row.wind_direction,
        wind_gust=row.wind_gust,
        rain=row.rain,
        uv_index=row.uv_index,
        illuminance=row.illuminance,
    )


@router.get(
    "/history",
    response_model=list[WeatherResponse],
    summary="Get historical weather data",
    description="Returns weather data points for the specified time range.",
)
async def get_weather_history(
    range: Literal["1h", "6h", "12h", "24h", "7d", "30d"] = Query(
        default="24h",
        description="Time range to query",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[WeatherResponse]:
    """Return weather data points within the specified time range.

    For longer ranges, data is sampled to keep response size manageable:
    - 1h-24h: raw data points
    - 7d: one point every 15 minutes
    - 30d: one point every hour
    """
    interval_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "12h": timedelta(hours=12),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    since = datetime.now(timezone.utc) - interval_map[range]

    # For longer ranges, use TimescaleDB time_bucket to downsample
    if range in ("7d", "30d"):
        bucket_size = "15 minutes" if range == "7d" else "1 hour"
        result = await db.execute(
            text(f"""
                SELECT
                    time_bucket(:bucket, time) AS time,
                    AVG(temperature) AS temperature,
                    AVG(humidity) AS humidity,
                    AVG(pressure) AS pressure,
                    AVG(wind_speed) AS wind_speed,
                    AVG(wind_direction) AS wind_direction,
                    MAX(wind_gust) AS wind_gust,
                    SUM(rain) AS rain,
                    MAX(uv_index) AS uv_index,
                    AVG(illuminance) AS illuminance
                FROM weather_data
                WHERE time >= :since
                GROUP BY 1
                ORDER BY 1 ASC
            """),
            {"bucket": bucket_size, "since": since},
        )
    else:
        result = await db.execute(
            text("""
                SELECT time, temperature, humidity, pressure,
                       wind_speed, wind_direction, wind_gust,
                       rain, uv_index, illuminance
                FROM weather_data
                WHERE time >= :since
                ORDER BY time ASC
            """),
            {"since": since},
        )

    rows = result.fetchall()

    return [
        WeatherResponse(
            time=row.time,
            temperature=row.temperature,
            humidity=row.humidity,
            pressure=row.pressure,
            wind_speed=row.wind_speed,
            wind_direction=row.wind_direction,
            wind_gust=row.wind_gust,
            rain=row.rain,
            uv_index=row.uv_index,
            illuminance=row.illuminance,
        )
        for row in rows
    ]


@router.get(
    "/stats",
    response_model=list[WeatherStatsResponse],
    summary="Get aggregated weather statistics",
    description="Returns min/max/avg statistics grouped by time period.",
)
async def get_weather_stats(
    period: Literal["hourly", "daily"] = Query(
        default="daily",
        description="Aggregation period",
    ),
    days: int = Query(
        default=7,
        ge=1,
        le=365,
        description="Number of days to look back",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[WeatherStatsResponse]:
    """Return aggregated weather statistics from continuous aggregates.

    Uses the pre-computed materialized views for efficient queries.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    view = "hourly_weather_stats" if period == "hourly" else "daily_weather_stats"

    result = await db.execute(
        text(f"""
            SELECT bucket, avg_temp, min_temp, max_temp,
                   avg_humidity, min_humidity, max_humidity,
                   avg_pressure, avg_wind_speed, max_wind_speed,
                   max_wind_gust, total_rain, max_uv_index,
                   avg_illuminance, sample_count
            FROM {view}
            WHERE bucket >= :since
            ORDER BY bucket ASC
        """),
        {"since": since},
    )

    rows = result.fetchall()

    return [
        WeatherStatsResponse(
            bucket=row.bucket,
            avg_temp=row.avg_temp,
            min_temp=row.min_temp,
            max_temp=row.max_temp,
            avg_humidity=row.avg_humidity,
            min_humidity=row.min_humidity,
            max_humidity=row.max_humidity,
            avg_pressure=row.avg_pressure,
            avg_wind_speed=row.avg_wind_speed,
            max_wind_speed=row.max_wind_speed,
            max_wind_gust=row.max_wind_gust,
            total_rain=row.total_rain,
            max_uv_index=row.max_uv_index,
            avg_illuminance=row.avg_illuminance,
            sample_count=row.sample_count,
        )
        for row in rows
    ]


@router.get(
    "/records/summary",
    response_model=WeatherRecordsSummaryResponse,
    summary="Get current historical weather records summary",
    description="Returns current daily, weekly, monthly, yearly, and all-time weather records.",
)
async def get_weather_records_summary(
    db: AsyncSession = Depends(get_db),
) -> WeatherRecordsSummaryResponse:
    """Return current records across all five time horizons in a single response."""
    tz_name = get_settings().tz
    period_keys = compute_period_keys(datetime.now(timezone.utc), tz_name)

    records_result = await db.execute(
        text("""
            SELECT period_type, metric, stat_type, value, recorded_at
            FROM weather_records
            WHERE (period_type = 'daily' AND period_key = :daily)
               OR (period_type = 'weekly' AND period_key = :weekly)
               OR (period_type = 'monthly' AND period_key = :monthly)
               OR (period_type = 'yearly' AND period_key = :yearly)
               OR (period_type = 'all_time' AND period_key = :all_time)
        """),
        period_keys,
    )
    record_rows = records_result.fetchall()

    keys_result = await db.execute(
        text("""
            SELECT period_type, period_key
            FROM weather_records
            GROUP BY period_type, period_key
            ORDER BY period_type ASC, period_key DESC
        """)
    )
    key_rows = keys_result.fetchall()

    grouped_rows: dict[str, list] = {pt: [] for pt in PERIOD_TYPES}
    for row in record_rows:
        if row.period_type in grouped_rows:
            grouped_rows[row.period_type].append(row)

    grouped_keys: dict[str, list[str]] = {pt: [] for pt in PERIOD_TYPES}
    for row in key_rows:
        if row.period_type in grouped_keys and len(grouped_keys[row.period_type]) < 60:
            grouped_keys[row.period_type].append(row.period_key)

    payload = {
        pt: WeatherPeriodRecordsResponse(
            period_type=pt,
            period_key=period_keys[pt],
            records=rows_to_record_dict(grouped_rows[pt]),
            available_keys=grouped_keys[pt],
        )
        for pt in PERIOD_TYPES
    }
    return WeatherRecordsSummaryResponse(timezone=tz_name, **payload)


@router.get(
    "/records",
    response_model=WeatherPeriodRecordsResponse,
    summary="Get historical weather records for a period",
    description="Returns min/max/sum weather records with exact timestamps for a given period.",
)
async def get_weather_records(
    period: Literal["daily", "weekly", "monthly", "yearly", "all_time"] = Query(
        default="daily",
        description="Aggregation period",
    ),
    key: Optional[str] = Query(
        default=None,
        max_length=20,
        description="Specific period key (e.g. 2026-11-26, 2026-W48, 2026-11, 2026, all)",
    ),
    db: AsyncSession = Depends(get_db),
) -> WeatherPeriodRecordsResponse:
    """Return historical records and available keys for a specific period."""
    tz_name = get_settings().tz
    target_key = key or compute_period_keys(datetime.now(timezone.utc), tz_name)[period]

    records_result = await db.execute(
        text("""
            SELECT metric, stat_type, value, recorded_at
            FROM weather_records
            WHERE period_type = :period_type AND period_key = :period_key
        """),
        {"period_type": period, "period_key": target_key},
    )
    keys_result = await db.execute(
        text("""
            SELECT period_key
            FROM weather_records
            WHERE period_type = :period_type
            GROUP BY period_key
            ORDER BY period_key DESC
            LIMIT 60
        """),
        {"period_type": period},
    )

    available_keys = [row.period_key for row in keys_result.fetchall()]
    return WeatherPeriodRecordsResponse(
        period_type=period,
        period_key=target_key,
        records=rows_to_record_dict(records_result.fetchall()),
        available_keys=available_keys,
    )
