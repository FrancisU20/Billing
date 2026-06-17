from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MARKUP_PCT = Decimal("0.12")
_MARKUP_DISPLAY_PCT = "12"


def gross_price(net: str) -> str:
    """Apply the platform markup to a net price and return the gross amount."""
    return f"{(Decimal(net) * (1 + MARKUP_PCT)).quantize(Decimal('0.01'), ROUND_HALF_UP):.2f}"


def markup_display_pct() -> str:
    return _MARKUP_DISPLAY_PCT
