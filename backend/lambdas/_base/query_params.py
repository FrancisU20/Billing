from __future__ import annotations

"""Shared query parameter parsing helpers for Lambda handlers."""

from enum import Enum

from shared.db.limits import DEFAULT_LIST_LIMIT, clamp_list_limit
from shared.errors import ValidationError


def parse_list_limit(params: dict) -> int:
    try:
        limit = int(params.get("limit", DEFAULT_LIST_LIMIT))
    except (TypeError, ValueError) as exc:
        raise ValidationError("limit debe ser un número entero") from exc
    if limit < 1:
        raise ValidationError("limit debe ser mayor a cero")
    return clamp_list_limit(limit)


def parse_enum_query_param(
    params: dict,
    name: str,
    enum_cls: type[Enum],
    *,
    error_message: str,
) -> str | None:
    value = params.get(name)
    if not value:
        return None
    try:
        enum_cls(value)
    except ValueError as exc:
        raise ValidationError(error_message) from exc
    return value
