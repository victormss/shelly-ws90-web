"""Unit tests for persistent historical weather records."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import WeatherRecord
from app.routers.weather import get_weather_records, get_weather_records_summary
from app.schemas import (
    RecordEntry,
    WeatherIngest,
    WeatherPeriodRecordsResponse,
    WeatherRecordsSummaryResponse,
)
from app.services.records import (
    build_record_batches,
    compute_period_keys,
    rows_to_record_dict,
)


def test_compute_period_keys_madrid_midnight_crossover():
    """UTC 23:15 on 2026-11-25 maps to 2026-11-26 in Europe/Madrid (UTC+1)."""
    dt = datetime(2026, 11, 25, 23, 15, tzinfo=timezone.utc)
    keys = compute_period_keys(dt, "Europe/Madrid")
    assert keys == {
        "daily": "2026-11-26",
        "weekly": "2026-W48",
        "monthly": "2026-11",
        "yearly": "2026",
        "all_time": "all",
    }


def test_compute_period_keys_madrid_same_day():
    """UTC 22:48 on 2026-11-25 stays on 2026-11-25 in Europe/Madrid (23:48)."""
    dt = datetime(2026, 11, 25, 22, 48, tzinfo=timezone.utc)
    keys = compute_period_keys(dt, "Europe/Madrid")
    assert keys["daily"] == "2026-11-25"
    assert keys["weekly"] == "2026-W48"


def test_compute_period_keys_iso_week_boundary():
    """ISO week formatting handles week 01 cleanly."""
    dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    keys = compute_period_keys(dt, "Europe/Madrid")
    assert keys["weekly"] == "2026-W01"
    assert keys["daily"] == "2026-01-01"


def test_build_record_batches_full_payload():
    """Full WeatherIngest payload generates expected max, min, and sum rows across 5 periods."""
    dt = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    data = WeatherIngest(
        temperature=15.5,
        humidity=70.0,
        pressure=1015.0,
        wind_speed=10.0,
        wind_direction=180.0,
        wind_gust=22.0,
        rain=0.4,
        uv_index=3.0,
        illuminance=20000.0,
    )
    max_rows, min_rows, sum_rows = build_record_batches(dt, data, "Europe/Madrid")
    assert len(max_rows) == 8 * 5
    assert len(min_rows) == 3 * 5
    assert len(sum_rows) == 1 * 5
    assert all(row["recorded_at"] == dt for row in max_rows + min_rows + sum_rows)


def test_build_record_batches_skips_none_fields():
    """All-None or partial payloads skip missing metrics cleanly."""
    dt = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)
    empty_max, empty_min, empty_sum = build_record_batches(dt, WeatherIngest(), "Europe/Madrid")
    assert (empty_max, empty_min, empty_sum) == ([], [], [])

    partial = WeatherIngest(temperature=12.0, uv_index=2.0)
    p_max, p_min, p_sum = build_record_batches(dt, partial, "Europe/Madrid")
    assert len(p_max) == 2 * 5
    assert len(p_min) == 1 * 5
    assert len(p_sum) == 0


def test_weather_record_model_metadata():
    """WeatherRecord maps to weather_records with expected composite primary key."""
    assert WeatherRecord.__tablename__ == "weather_records"
    pk_cols = [col.name for col in WeatherRecord.__table__.primary_key.columns]
    assert pk_cols == ["period_type", "period_key", "metric", "stat_type"]


def test_rows_to_record_dict_and_schemas():
    """rows_to_record_dict builds RecordEntry instances compatible with response schemas."""
    ts = datetime(2026, 11, 26, 11, 30, tzinfo=timezone.utc)
    rows = [
        SimpleNamespace(metric="temperature", stat_type="max", value=18.2, recorded_at=ts),
        SimpleNamespace(metric="rain", stat_type="sum", value=1.4, recorded_at=ts),
    ]
    mapped = rows_to_record_dict(rows)
    assert isinstance(mapped["temperature_max"], RecordEntry)
    assert mapped["temperature_max"].value == 18.2
    assert mapped["rain_sum"].value == 1.4

    period_resp = WeatherPeriodRecordsResponse(
        period_type="daily",
        period_key="2026-11-26",
        records=mapped,
        available_keys=["2026-11-26", "2026-11-25"],
    )
    summary_resp = WeatherRecordsSummaryResponse(
        timezone="Europe/Madrid",
        daily=period_resp,
        weekly=period_resp,
        monthly=period_resp,
        yearly=period_resp,
        all_time=period_resp,
    )
    assert summary_resp.daily.records["temperature_max"].recorded_at == ts


@pytest.mark.asyncio
async def test_get_weather_records_endpoint_with_mock_db():
    """get_weather_records returns populated and empty responses cleanly."""
    ts = datetime(2026, 11, 25, 22, 0, tzinfo=timezone.utc)
    records_res = MagicMock()
    records_res.fetchall.return_value = [
        SimpleNamespace(metric="temperature", stat_type="min", value=6.3, recorded_at=ts),
    ]
    keys_res = MagicMock()
    keys_res.fetchall.return_value = [
        SimpleNamespace(period_key="2026-11-26"),
        SimpleNamespace(period_key="2026-11-25"),
    ]
    db = AsyncMock()
    db.execute.side_effect = [records_res, keys_res]

    resp = await get_weather_records(period="daily", key="2026-11-25", db=db)
    assert resp.period_type == "daily"
    assert resp.period_key == "2026-11-25"
    assert resp.records["temperature_min"].value == 6.3
    assert resp.available_keys == ["2026-11-26", "2026-11-25"]


@pytest.mark.asyncio
async def test_get_weather_records_summary_endpoint_with_mock_db():
    """get_weather_records_summary aggregates records and available keys across all 5 periods."""
    ts = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)
    records_res = MagicMock()
    records_res.fetchall.return_value = [
        SimpleNamespace(period_type="daily", metric="temperature", stat_type="max", value=10.1, recorded_at=ts),
        SimpleNamespace(period_type="all_time", metric="temperature", stat_type="max", value=10.1, recorded_at=ts),
    ]
    keys_res = MagicMock()
    keys_res.fetchall.return_value = [
        SimpleNamespace(period_type="daily", period_key="2026-11-26"),
        SimpleNamespace(period_type="daily", period_key="2026-11-25"),
        SimpleNamespace(period_type="all_time", period_key="all"),
    ]
    db = AsyncMock()
    db.execute.side_effect = [records_res, keys_res]

    resp = await get_weather_records_summary(db=db)
    assert resp.timezone == "Europe/Madrid"
    assert resp.daily.records["temperature_max"].value == 10.1
    assert resp.daily.available_keys == ["2026-11-26", "2026-11-25"]
    assert resp.all_time.period_key == "all"
    assert resp.weekly.records == {}
