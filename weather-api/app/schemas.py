"""Weather Station API — Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ─── Ingest (request from Home Assistant) ───

class WeatherIngest(BaseModel):
    """Schema for weather data ingestion from Home Assistant."""

    temperature: Optional[float] = Field(None, description="Temperature in °C", ge=-60, le=60)
    humidity: Optional[float] = Field(None, description="Relative humidity in %", ge=0, le=100)
    pressure: Optional[float] = Field(None, description="Atmospheric pressure in hPa", ge=800, le=1100)
    wind_speed: Optional[float] = Field(None, description="Wind speed in km/h", ge=0, le=500)
    wind_direction: Optional[float] = Field(None, description="Wind direction in degrees", ge=0, le=360)
    wind_gust: Optional[float] = Field(None, description="Wind gust in km/h", ge=0, le=500)
    rain: Optional[float] = Field(None, description="Rain accumulation in mm", ge=0)
    uv_index: Optional[float] = Field(None, description="UV index", ge=0, le=20)
    illuminance: Optional[float] = Field(None, description="Light level in lux", ge=0)

    class Config:
        json_schema_extra = {
            "example": {
                "temperature": 22.5,
                "humidity": 65.0,
                "pressure": 1013.25,
                "wind_speed": 12.3,
                "wind_direction": 180.0,
                "wind_gust": 25.1,
                "rain": 0.0,
                "uv_index": 3.0,
                "illuminance": 45000.0,
            }
        }


# ─── Response schemas ───

class WeatherResponse(BaseModel):
    """Single weather data point response."""

    time: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    pressure: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    wind_gust: Optional[float] = None
    rain: Optional[float] = None
    uv_index: Optional[float] = None
    illuminance: Optional[float] = None


class WeatherStatsResponse(BaseModel):
    """Aggregated weather statistics response."""

    bucket: datetime
    avg_temp: Optional[float] = None
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    avg_humidity: Optional[float] = None
    min_humidity: Optional[float] = None
    max_humidity: Optional[float] = None
    avg_pressure: Optional[float] = None
    avg_wind_speed: Optional[float] = None
    max_wind_speed: Optional[float] = None
    max_wind_gust: Optional[float] = None
    total_rain: Optional[float] = None
    max_uv_index: Optional[float] = None
    avg_illuminance: Optional[float] = None
    sample_count: int = 0


class IngestResponse(BaseModel):
    """Response after successful data ingestion."""

    status: str = "ok"
    message: str = "Data ingested successfully"
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    database: str = "connected"
