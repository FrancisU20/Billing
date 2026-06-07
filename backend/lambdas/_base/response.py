"""
Standard HTTP responses for all Lambdas.

Single format:
    {
        "success": true | false,
        "data":    <payload> | null,
        "error":   null | {"code": "...", "message": "..."},
        "meta":    {"request_id": "...", "timestamp": "..."}
    }

Never change this format from individual Lambdas.
The frontend depends on this contract.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from shared.errors import AppError


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers":    {"Content-Type": "application/json"},
        "body":       json.dumps(body, default=str),
    }


class ApiResponse:

    @staticmethod
    def ok(data: Any, request_id: str) -> dict:
        return _build(200, {
            "success": True,
            "data":    data,
            "error":   None,
            "meta":    {"request_id": request_id, "timestamp": _ts()},
        })

    @staticmethod
    def created(data: Any, request_id: str) -> dict:
        return _build(201, {
            "success": True,
            "data":    data,
            "error":   None,
            "meta":    {"request_id": request_id, "timestamp": _ts()},
        })

    @staticmethod
    def no_content(request_id: str) -> dict:
        return _build(204, {
            "success": True,
            "data":    None,
            "error":   None,
            "meta":    {"request_id": request_id, "timestamp": _ts()},
        })

    @staticmethod
    def paginated(
        items:      list,
        next_token: str | None,
        request_id: str,
        total:      int | None = None,
    ) -> dict:
        data: dict[str, Any] = {
            "items":      items,
            "next_token": next_token,
            "has_more":   next_token is not None,
        }
        if total is not None:
            data["total"] = total
        return _build(200, {
            "success": True,
            "data":    data,
            "error":   None,
            "meta":    {"request_id": request_id, "timestamp": _ts()},
        })

    @staticmethod
    def error(err: AppError, request_id: str) -> dict:
        return _build(err.status_code, {
            "success": False,
            "data":    None,
            "error":   {
                "code":    err.code,
                "message": err.default_message,
            },
            "meta": {"request_id": request_id, "timestamp": _ts()},
        })
