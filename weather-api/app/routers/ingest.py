"""Weather Station API — Ingest router (protected)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.database import get_db
from app.models import WeatherData
from app.schemas import WeatherIngest, IngestResponse
from app.auth import verify_api_key

router = APIRouter(prefix="/api/weather", tags=["ingest"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest weather data from Home Assistant",
    description="Protected endpoint. Requires Bearer token authentication.",
)
async def ingest_weather_data(
    data: WeatherIngest,
    _api_key: str = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    """Receive and store a weather data point from Home Assistant.

    The API key must match the configured API_SECRET_KEY.
    Data is inserted into the TimescaleDB hypertable.
    """
    now = datetime.now(timezone.utc)

    record = WeatherData(
        time=now,
        temperature=data.temperature,
        humidity=data.humidity,
        pressure=data.pressure,
        wind_speed=data.wind_speed,
        wind_direction=data.wind_direction,
        wind_gust=data.wind_gust,
        rain=data.rain,
        uv_index=data.uv_index,
        illuminance=data.illuminance,
    )

    db.add(record)
    await db.commit()

    return IngestResponse(
        status="ok",
        message="Data ingested successfully",
        timestamp=now,
    )
