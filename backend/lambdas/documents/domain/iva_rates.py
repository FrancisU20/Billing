from __future__ import annotations

from datetime import date
from decimal import Decimal

IVA_RATES: list[dict] = [
    {"from": date(2024, 4, 1), "to": None, "pct": Decimal("15")},
    {"from": date(2024, 1, 1), "to": date(2024, 3, 31), "pct": Decimal("12")},
]


def iva_rate_for(issued_at: date) -> Decimal:
    """Return the standard IVA percentage applicable on issued_at."""
    for band in IVA_RATES:
        if issued_at >= band["from"] and (band["to"] is None or issued_at <= band["to"]):
            return band["pct"]
    raise ValueError(f"No IVA rate defined for {issued_at}")
