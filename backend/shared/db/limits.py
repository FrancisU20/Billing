from __future__ import annotations

DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 100


def clamp_list_limit(limit: int) -> int:
    return min(limit, MAX_LIST_LIMIT)
