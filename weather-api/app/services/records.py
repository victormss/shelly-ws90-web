"""Weather Station API — Persistent historical records service."""

from datetime import datetime, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WeatherRecord
from app.schemas import RecordEntry, WeatherIngest

PERIOD_TYPES = ("daily", "weekly", "monthly", "yearly", "all_time")

MAX_METRICS = (
    "temperature",
    "humidity",
    "pressure",
    "wind_speed",
    "wind_gust",
    "rain",
    "uv_index",
    "illuminance",
)
MIN_METRICS = ("temperature", "humidity", "pressure")
SUM_METRICS = ("rain",)

PK_COLUMNS = ["period_type", "period_key", "metric", "stat_type"]


def compute_period_keys(dt: datetime, tz_name: str = "Europe/Madrid") -> dict[str, str]:
    """Compute period keys for all horizons in the configured local timezone."""
    aware_dt = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    local_dt = aware_dt.astimezone(ZoneInfo(tz_name))
    iso = local_dt.isocalendar()
    return {
        "daily": local_dt.strftime("%Y-%m-%d"),
        "weekly": f"{iso.year}-W{iso.week:02d}",
        "monthly": local_dt.strftime("%Y-%m"),
        "yearly": local_dt.strftime("%Y"),
        "all_time": "all",
    }


def _build_rows_for_stat(
    period_keys: dict[str, str],
    metrics: Iterable[str],
    stat_type: str,
    data: WeatherIngest,
    recorded_at: datetime,
) -> list[dict]:
    """Build row dictionaries for a given stat_type, skipping None metric values."""
    rows: list[dict] = []
    for metric in metrics:
        value = getattr(data, metric)
        if value is None:
            continue
        for period_type, period_key in period_keys.items():
            rows.append(
                {
                    "period_type": period_type,
                    "period_key": period_key,
                    "metric": metric,
                    "stat_type": stat_type,
                    "value": float(value),
                    "recorded_at": recorded_at,
                }
            )
    return rows


def build_record_batches(
    recorded_at: datetime,
    data: WeatherIngest,
    tz_name: str = "Europe/Madrid",
) -> tuple[list[dict], list[dict], list[dict]]:
    """Build (max_rows, min_rows, sum_rows) upsert batches for a weather reading."""
    period_keys = compute_period_keys(recorded_at, tz_name)
    max_rows = _build_rows_for_stat(period_keys, MAX_METRICS, "max", data, recorded_at)
    min_rows = _build_rows_for_stat(period_keys, MIN_METRICS, "min", data, recorded_at)
    sum_rows = _build_rows_for_stat(period_keys, SUM_METRICS, "sum", data, recorded_at)
    return max_rows, min_rows, sum_rows


async def _upsert_extrema_batch(
    db: AsyncSession,
    rows: list[dict],
    is_max: bool,
) -> None:
    """Execute an atomic PostgreSQL upsert for min or max record batches."""
    if not rows:
        return
    stmt = pg_insert(WeatherRecord).values(rows)
    condition = (
        stmt.excluded.value > WeatherRecord.value
        if is_max
        else stmt.excluded.value < WeatherRecord.value
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=PK_COLUMNS,
        set_={
            "value": stmt.excluded.value,
            "recorded_at": stmt.excluded.recorded_at,
            "updated_at": func.now(),
        },
        where=condition,
    )
    await db.execute(stmt)


async def _upsert_sum_batch(db: AsyncSession, rows: list[dict]) -> None:
    """Execute an atomic PostgreSQL upsert accumulating rain totals."""
    if not rows:
        return
    stmt = pg_insert(WeatherRecord).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=PK_COLUMNS,
        set_={
            "value": WeatherRecord.value + stmt.excluded.value,
            "recorded_at": case(
                (stmt.excluded.value > 0, stmt.excluded.recorded_at),
                else_=WeatherRecord.recorded_at,
            ),
            "updated_at": func.now(),
        },
    )
    await db.execute(stmt)


async def upsert_weather_records(
    db: AsyncSession,
    recorded_at: datetime,
    data: WeatherIngest,
    tz_name: str = "Europe/Madrid",
) -> None:
    """Update persistent weather records for all five periods inside the active transaction."""
    max_rows, min_rows, sum_rows = build_record_batches(recorded_at, data, tz_name)
    await _upsert_extrema_batch(db, max_rows, is_max=True)
    await _upsert_extrema_batch(db, min_rows, is_max=False)
    await _upsert_sum_batch(db, sum_rows)


def rows_to_record_dict(rows: Iterable) -> dict[str, RecordEntry]:
    """Convert SQLAlchemy rows into a mapping keyed by '<metric>_<stat_type>'."""
    records: dict[str, RecordEntry] = {}
    for row in rows:
        key = f"{row.metric}_{row.stat_type}"
        records[key] = RecordEntry(value=row.value, recorded_at=row.recorded_at)
    return records
