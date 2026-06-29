from __future__ import annotations

"""Small text-search helpers for in-memory list filters."""

from typing import Any


def normalize_search_query(value: str | None) -> str:
    return value.strip().casefold() if value else ""


def matches_search_query(query: str, *candidates: Any) -> bool:
    if not query:
        return True
    return any(
        query in str(candidate).casefold() for candidate in candidates if candidate is not None
    )
