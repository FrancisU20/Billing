from __future__ import annotations

import re
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from shared.errors import ValidationError

_DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}")
ECUADOR_TIME_ZONE = "America/Guayaquil"
ECUADOR_TZ = ZoneInfo(ECUADOR_TIME_ZONE)


def now_utc() -> datetime:
    """Technical instant for persistence, TTLs, locks and external protocols."""
    return datetime.now(UTC)


def now_ecuador() -> datetime:
    """Current civil time in Ecuador for user-facing/business timestamps."""
    return now_utc().astimezone(ECUADOR_TZ)


def today_ecuador() -> date:
    return now_ecuador().date()


def to_ecuador(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ECUADOR_TZ)


def isoformat_ecuador(value: datetime | None) -> str | None:
    if value is None:
        return None
    return to_ecuador(value).isoformat()


def current_ecuador_month_utc_bounds(now: datetime | None = None) -> tuple[str, str]:
    local_now = to_ecuador(now or now_utc())
    start_local = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start_local.month == 12:
        next_month = start_local.replace(year=start_local.year + 1, month=1)
    else:
        next_month = start_local.replace(month=start_local.month + 1)
    end_local = next_month - timedelta(microseconds=1)
    return start_local.astimezone(UTC).isoformat(), end_local.astimezone(UTC).isoformat()


def current_ecuador_year_utc_bounds(now: datetime | None = None) -> tuple[str, str]:
    local_now = to_ecuador(now or now_utc())
    start_local = local_now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    next_year = start_local.replace(year=start_local.year + 1)
    end_local = next_year - timedelta(microseconds=1)
    return start_local.astimezone(UTC).isoformat(), end_local.astimezone(UTC).isoformat()


def current_ecuador_previous_month_utc_bounds(now: datetime | None = None) -> tuple[str, str]:
    local_now = to_ecuador(now or now_utc())
    this_month_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if this_month_start.month == 1:
        start_local = this_month_start.replace(year=this_month_start.year - 1, month=12)
    else:
        start_local = this_month_start.replace(month=this_month_start.month - 1)
    end_local = this_month_start - timedelta(microseconds=1)
    return start_local.astimezone(UTC).isoformat(), end_local.astimezone(UTC).isoformat()


def current_ecuador_previous_year_utc_bounds(now: datetime | None = None) -> tuple[str, str]:
    local_now = to_ecuador(now or now_utc())
    this_year_start = local_now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    start_local = this_year_start.replace(year=this_year_start.year - 1)
    end_local = this_year_start - timedelta(microseconds=1)
    return start_local.astimezone(UTC).isoformat(), end_local.astimezone(UTC).isoformat()


def parse_datetime_as_ecuador(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ECUADOR_TZ)
    return parsed.astimezone(UTC)


def format_date_ecuador(value: date | datetime | str | None) -> str:
    if not value:
        return "No disponible"
    try:
        parsed = _coerce_date_or_datetime(value)
    except ValueError:
        return str(value)
    if isinstance(parsed, datetime):
        parsed = to_ecuador(parsed).date()
    return parsed.strftime("%d-%m-%Y")


def format_datetime_ecuador(value: datetime | str | None) -> str:
    if not value:
        return "No disponible"
    try:
        parsed = _coerce_datetime(value)
    except ValueError:
        return str(value)
    return to_ecuador(parsed).strftime("%d-%m-%Y %H:%M")


def _coerce_date_or_datetime(value: date | datetime | str) -> date | datetime:
    if isinstance(value, datetime | date):
        return value
    normalized = value.replace("Z", "+00:00")
    if "T" in normalized or " " in normalized:
        return _coerce_datetime(normalized)
    return date.fromisoformat(normalized)


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return parse_datetime_as_ecuador(value)


def parse_date_boundary(value: str | None, *, end_of_day: bool) -> str | None:
    """Normalize a local Ecuador `created_from`/`created_to` param into a UTC boundary.

    Stored timestamps remain UTC so DynamoDB range filters stay stable with
    existing data. Bare dates (`YYYY-MM-DD`) are expanded using Ecuador civil
    day boundaries, then converted to UTC for the repository filter.
    """
    if not value:
        return None
    raw = value.strip()
    try:
        if _DATE_ONLY.fullmatch(raw):
            boundary = time.max if end_of_day else time.min
            parsed = datetime.combine(
                datetime.fromisoformat(raw).date(), boundary, tzinfo=ECUADOR_TZ
            )
        else:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=ECUADOR_TZ)
    except ValueError as exc:
        raise ValidationError("Fecha de creación inválida") from exc
    return parsed.astimezone(UTC).isoformat()
