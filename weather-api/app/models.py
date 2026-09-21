"""Weather Station API — SQLAlchemy models."""

from sqlalchemy import Column, Float, DateTime, func
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class WeatherData(Base):
    """Weather data point from the WS90 station.

    Maps to the 'weather_data' hypertable created in init.sql.
    TimescaleDB manages partitioning automatically via the 'time' column.
    """

    __tablename__ = "weather_data"

    time = Column(
        DateTime(timezone=True),
        primary_key=True,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    temperature = Column(Float, nullable=True, comment="Temperature in °C")
    humidity = Column(Float, nullable=True, comment="Relative humidity in %")
    pressure = Column(Float, nullable=True, comment="Atmospheric pressure in hPa")
    wind_speed = Column(Float, nullable=True, comment="Wind speed in km/h")
    wind_direction = Column(Float, nullable=True, comment="Wind direction in degrees")
    wind_gust = Column(Float, nullable=True, comment="Wind gust in km/h")
    rain = Column(Float, nullable=True, comment="Rain accumulation in mm")
    uv_index = Column(Float, nullable=True, comment="UV index")
    illuminance = Column(Float, nullable=True, comment="Light level in lux")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "time": self.time.isoformat() if self.time else None,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "pressure": self.pressure,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "wind_gust": self.wind_gust,
            "rain": self.rain,
            "uv_index": self.uv_index,
            "illuminance": self.illuminance,
        }
