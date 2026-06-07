from __future__ import annotations
"""
HTTP idempotency for mutating operations.

Responsibilities:
- Require `X-Idempotency-Key`.
- Bind the key to method + path + body_hash.
- Return the cached response if the operation already completed.
- Reserve the key as IN_PROGRESS before running the handler.
- Expose a context so the repository can mark COMPLETED within the same
  DynamoDB transaction that persists the business change.
"""

import functools
import json
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from shared.config import env
from shared.db.client import get_table
from shared.errors import (
    DatabaseError,
    IdempotencyInProgressError,
    IdempotencyKeyReusedError,
    ValidationError,
)
from shared.logger import get_logger

_log = get_logger(__name__)

_TABLE_ENV                 = "IDEMPOTENCY_TABLE"
_TABLE_NAME                = env(_TABLE_ENV, "")
_IN_PROGRESS_TTL_SECONDS   = 900
_COMPLETED_TTL_SECONDS     = 86_400
_FAILED_TTL_SECONDS        = 60

_table = None
_current_ctx: ContextVar["IdempotencyContext | None"] = ContextVar(
    "idempotency_ctx", default=None
)


@dataclass
class IdempotencyContext:
    table_name: str
    pk: str
    key: str
    method: str
    path: str
    body_hash: str
    completed: bool = False


def _get_table():
    global _table
    if _table is None and _TABLE_NAME:
        _table = get_table(_TABLE_ENV)
    return _table


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _epoch_plus(seconds: int) -> int:
    return int(_now().timestamp()) + seconds



def _scope_for(request) -> str:
    if request.tenant_id:
        return f"TENANT#{request.tenant_id}"
    return f"GLOBAL#{request.user_id or 'anonymous'}"


def _context_for(request) -> IdempotencyContext:
    return IdempotencyContext(
        table_name = _TABLE_NAME,
        pk         = f"{_scope_for(request)}#{request.idempotency_key}",
        key        = request.idempotency_key,
        method     = request.method,
        path       = request.path,
        body_hash  = request.body_hash,
    )


def _matches(item: dict, ctx: IdempotencyContext) -> bool:
    return (
        item.get("method") == ctx.method
        and item.get("path") == ctx.path
        and item.get("body_hash") == ctx.body_hash
    )


def _is_expired(item: dict) -> bool:
    ttl = item.get("ttl")
    return bool(ttl and int(ttl) < int(_now().timestamp()))


def _existing(table, ctx: IdempotencyContext) -> dict | None:
    try:
        resp = table.get_item(Key={"pk": ctx.pk}, ConsistentRead=True)
        return resp.get("Item")
    except ClientError as exc:
        _log.error("idempotency: error reading key", error=str(exc))
        raise DatabaseError()


def _reserve(table, ctx: IdempotencyContext) -> None:
    now = _now()
    try:
        table.put_item(
            Item={
                "pk":         ctx.pk,
                "key":        ctx.key,
                "method":     ctx.method,
                "path":       ctx.path,
                "body_hash":  ctx.body_hash,
                "status":     "IN_PROGRESS",
                "created_at": now.isoformat(),
                "ttl":        _epoch_plus(_IN_PROGRESS_TTL_SECONDS),
            },
            ConditionExpression=(
                Attr("pk").not_exists()
                | Attr("ttl").lt(int(now.timestamp()))
                | Attr("status").eq("FAILED")
            ),
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            item = _existing(table, ctx)
            if item and not _matches(item, ctx):
                raise IdempotencyKeyReusedError()
            if item and item.get("status") == "COMPLETED" and item.get("response"):
                return
            raise IdempotencyInProgressError()
        _log.error("idempotency: error reserving key", error=str(exc))
        raise DatabaseError()


def _mark_failed(table, ctx: IdempotencyContext) -> None:
    try:
        table.update_item(
            Key={"pk": ctx.pk},
            UpdateExpression="SET #status = :status, failed_at = :failed_at, #ttl = :ttl",
            ConditionExpression=Attr("status").eq("IN_PROGRESS"),
            ExpressionAttributeNames={"#status": "status", "#ttl": "ttl"},
            ExpressionAttributeValues={
                ":status":    "FAILED",
                ":failed_at": _now().isoformat(),
                ":ttl":       _epoch_plus(_FAILED_TTL_SECONDS),
            },
        )
    except ClientError as exc:
        _log.warning("idempotency: could not mark FAILED", error=str(exc))


def _mark_completed_non_transactional(table, ctx: IdempotencyContext, response: dict) -> None:
    try:
        table.update_item(
            Key={"pk": ctx.pk},
            UpdateExpression=(
                "SET #status = :completed, #response = :response, "
                "completed_at = :completed_at, #ttl = :ttl"
            ),
            ConditionExpression=Attr("status").eq("IN_PROGRESS"),
            ExpressionAttributeNames={"#status": "status", "#response": "response", "#ttl": "ttl"},
            ExpressionAttributeValues={
                ":completed":    "COMPLETED",
                ":response":     json.dumps(response, default=str),
                ":completed_at": _now().isoformat(),
                ":ttl":          _epoch_plus(_COMPLETED_TTL_SECONDS),
            },
        )
        ctx.completed = True
    except ClientError as exc:
        _log.error("idempotency: could not cache response", error=str(exc))
        raise DatabaseError()


def current_context() -> IdempotencyContext | None:
    return _current_ctx.get()


def require_current_context() -> IdempotencyContext:
    ctx = current_context()
    if ctx is None:
        raise ValidationError("X-Idempotency-Key es requerido")
    return ctx


def mark_completed() -> None:
    ctx = require_current_context()
    ctx.completed = True


def completion_transact_item(ctx: IdempotencyContext, response: dict) -> dict:
    """Return the transactional Update that closes out idempotency."""
    return {
        "Update": {
            "TableName": ctx.table_name,
            "Key": {"pk": ctx.pk},
            "UpdateExpression": (
                "SET #status = :completed, #response = :response, "
                "completed_at = :completed_at, #ttl = :ttl"
            ),
            "ConditionExpression": (
                "#status = :in_progress AND #method = :method "
                "AND #path = :path AND #body_hash = :body_hash"
            ),
            "ExpressionAttributeNames": {
                "#status":    "status",
                "#path":      "path",
                "#response":  "response",
                "#ttl":       "ttl",
                "#method":    "method",
                "#body_hash": "body_hash",
            },
            "ExpressionAttributeValues": {
                ":completed":    "COMPLETED",
                ":in_progress":  "IN_PROGRESS",
                ":response":     json.dumps(response, default=str),
                ":completed_at": _now().isoformat(),
                ":ttl":          _epoch_plus(_COMPLETED_TTL_SECONDS),
                ":method":       ctx.method,
                ":path":         ctx.path,
                ":body_hash":    ctx.body_hash,
            },
        }
    }


def idempotent(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(request, context):
        if not _TABLE_NAME:
            return func(request, context)
        if not request.idempotency_key:
            raise ValidationError("X-Idempotency-Key es requerido")

        table = _get_table()
        ctx = _context_for(request)
        item = _existing(table, ctx)
        if item and item.get("status") != "FAILED" and not _is_expired(item):
            if not _matches(item, ctx):
                raise IdempotencyKeyReusedError()
            if item.get("status") == "COMPLETED" and item.get("response"):
                _log.info("idempotency: returning cached response", key=ctx.key)
                return json.loads(item["response"])
            raise IdempotencyInProgressError()

        _reserve(table, ctx)
        token = _current_ctx.set(ctx)
        try:
            response = func(request, context)
            if not ctx.completed:
                _mark_completed_non_transactional(table, ctx, response)
            return response
        except Exception:
            if not ctx.completed:
                _mark_failed(table, ctx)
            raise
        finally:
            _current_ctx.reset(token)

    return wrapper
