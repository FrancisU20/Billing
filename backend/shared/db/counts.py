from __future__ import annotations

from collections.abc import Callable
from typing import Any


def paginated_count(operation: Callable[..., dict], **kwargs: Any) -> int:
    count_kwargs = dict(kwargs)
    total = 0
    while True:
        response = operation(**count_kwargs)
        total += response.get("Count", 0)
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return total
        count_kwargs["ExclusiveStartKey"] = last_key
