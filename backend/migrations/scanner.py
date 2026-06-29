from __future__ import annotations

"""Shared DynamoDB scan helpers for data migrations."""

from collections.abc import Iterator
from typing import Any


def scan_all_items(
    table,
    *,
    scan_kwargs: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield every item from a paginated DynamoDB scan.

    Migration code should keep domain-specific filtering and updates local to the
    migration. This helper owns only the DynamoDB pagination protocol.
    """
    kwargs = dict(scan_kwargs or {})
    while True:
        response = table.scan(**kwargs)
        yield from response.get("Items", [])

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key
