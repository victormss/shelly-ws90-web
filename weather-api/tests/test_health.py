"""Smoke tests for the Weather Station API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture
def mock_settings():
    """Mock settings for tests that don't need real DB."""
    with patch("app.config.get_settings") as mock:
        settings = MagicMock()
        settings.app_name = "Weather Station API"
        settings.app_version = "1.0.0"
        settings.debug = True
        settings.allowed_origins = "*"
        settings.api_secret_key = "test-secret-key-for-testing-only"
        settings.database_url = "postgresql+asyncpg://test:test@localhost:5432/testdb"
        mock.return_value = settings
        yield settings


def test_schemas_import():
    """Schemas module imports correctly."""
    from app.schemas import (
        WeatherIngest,
        WeatherResponse,
        WeatherStatsResponse,
        IngestResponse,
        HealthResponse,
    )
    assert WeatherIngest is not None
    assert WeatherResponse is not None
    assert WeatherStatsResponse is not None
    assert IngestResponse is not None
    assert HealthResponse is not None


def test_weather_ingest_schema_valid():
    """WeatherIngest accepts valid data."""
    from app.schemas import WeatherIngest

    data = WeatherIngest(
        temperature=22.5,
        humidity=65.0,
        pressure=1013.25,
        wind_speed=12.3,
        wind_direction=180.0,
        wind_gust=25.1,
        rain=0.0,
        uv_index=3.0,
        illuminance=45000.0,
    )
    assert data.temperature == 22.5
    assert data.humidity == 65.0
    assert data.pressure == 1013.25


def test_weather_ingest_schema_optional_fields():
    """WeatherIngest accepts partial data (all fields optional)."""
    from app.schemas import WeatherIngest

    data = WeatherIngest(temperature=20.0)
    assert data.temperature == 20.0
    assert data.humidity is None
    assert data.rain is None


def test_weather_ingest_schema_rejects_invalid_temperature():
    """WeatherIngest rejects temperature outside valid range (-60, 60)."""
    from app.schemas import WeatherIngest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WeatherIngest(temperature=100.0)

    with pytest.raises(ValidationError):
        WeatherIngest(temperature=-80.0)


def test_weather_ingest_schema_rejects_invalid_humidity():
    """WeatherIngest rejects humidity outside valid range (0, 100)."""
    from app.schemas import WeatherIngest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WeatherIngest(humidity=150.0)


def test_health_response_defaults():
    """HealthResponse has correct default values."""
    from app.schemas import HealthResponse

    response = HealthResponse(version="1.0.0")
    assert response.status == "healthy"
    assert response.database == "connected"
    assert response.version == "1.0.0"


def test_ingest_response_defaults():
    """IngestResponse has correct default values."""
    from app.schemas import IngestResponse
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    response = IngestResponse(timestamp=now)
    assert response.status == "ok"
    assert response.message == "Data ingested successfully"
    assert response.timestamp == now


def test_models_import():
    """Models module imports correctly."""
    from app.models import WeatherData, Base
    assert WeatherData is not None
    assert Base is not None


def test_weather_data_model_tablename():
    """WeatherData model maps to correct table."""
    from app.models import WeatherData
    assert WeatherData.__tablename__ == "weather_data"
