from __future__ import annotations

import re
from datetime import UTC, datetime, time

from shared.errors import ValidationError

_DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse_date_boundary(value: str | None, *, end_of_day: bool) -> str | None:
    """Normalize a `created_from`/`created_to` query param into a UTC ISO boundary.

    Accepts a bare date (`YYYY-MM-DD`) — expanded to start/end of day — or a
    full ISO datetime. Used to build `created_at` range filters that compare
    lexicographically against stored ISO timestamps.
    """
    if not value:
        return None
    raw = value.strip()
    try:
        if _DATE_ONLY.fullmatch(raw):
            boundary = time.max if end_of_day else time.min
            parsed = datetime.combine(datetime.fromisoformat(raw).date(), boundary, tzinfo=UTC)
        else:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValidationError("Fecha de creación inválida") from exc
    return parsed.astimezone(UTC).isoformat()
