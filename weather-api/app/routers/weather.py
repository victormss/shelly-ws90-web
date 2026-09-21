"""Weather Station API — Public weather data endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Literal
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.schemas import WeatherResponse, WeatherStatsResponse

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
