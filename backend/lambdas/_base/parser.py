from __future__ import annotations
"""
HTTP API Gateway v2 event parser.

Extracts from the event:
- body (JSON)
- path_params, query_params, headers
- JWT claims: tenant_id, user_id, role, is_superadmin
- idempotency_key from the X-Idempotency-Key header

Security rule: tenant_id ALWAYS comes from the JWT — never from the body.
If the token has no tenant_id and is not superadmin, it is rejected with AuthError.

Also provides parse() to validate the body against a Pydantic schema.
"""

import json
import base64
import hashlib
from dataclasses import dataclass
from urllib.parse import urlencode
from typing import Type, TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from shared.errors import MissingTenantContextError, ValidationError

T = TypeVar("T", bound=BaseModel)


def _parse_body(event: dict) -> dict:
    raw_body = event.get("body")
    if not raw_body:
        return {}

    if event.get("isBase64Encoded"):
        try:
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        except Exception as exc:
            raise ValidationError("Body base64 inválido") from exc

    try:
        body = json.loads(raw_body)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValidationError("JSON inválido") from exc

    if body is None:
        return {}
    if not isinstance(body, dict):
        raise ValidationError("El body debe ser un objeto JSON")
    return body


def _body_hash(body: dict) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _path_with_query(path: str, query_params: dict) -> str:
    if not query_params:
        return path
    return f"{path}?{urlencode(sorted(query_params.items()))}"


@dataclass(frozen=True)
class Request:
    body:            dict
    path_params:     dict
    query_params:    dict
    headers:         dict
    tenant_id:       str
    user_id:         str
    role:            str
    is_superadmin:   bool
    request_id:      str
    idempotency_key: str | None
    method:          str
    path:            str
    body_hash:       str

    @classmethod
    def from_event(cls, event: dict, require_tenant: bool = True) -> "Request":
        ctx    = event.get("requestContext", {})
        http   = ctx.get("http", {})
        claims = ctx.get("authorizer", {}).get("jwt", {}).get("claims", {})
        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        body = _parse_body(event)
        query_params = event.get("queryStringParameters") or {}
        path = http.get("path", event.get("rawPath", ""))

        is_superadmin = claims.get("custom:is_superadmin", "false").lower() == "true"
        tenant_id     = claims.get("custom:tenant_id", "").strip()
        role          = claims.get("custom:role", "viewer")

        # Public routes (require_tenant=False) accept anonymous requests with no JWT.
        if require_tenant and not is_superadmin and not tenant_id:
            raise MissingTenantContextError()

        return cls(
            body            = body,
            path_params     = event.get("pathParameters")       or {},
            query_params    = query_params,
            headers         = headers,
            tenant_id       = tenant_id,
            user_id         = claims.get("sub", ""),
            role            = role,
            is_superadmin   = is_superadmin,
            request_id      = ctx.get("requestId", "local"),
            idempotency_key = headers.get("x-idempotency-key"),
            method          = http.get("method", ""),
            path            = _path_with_query(path, query_params),
            body_hash       = _body_hash(body),
        )


def parse(schema: Type[T], data: dict) -> T:
    """Validate `data` against the given Pydantic schema. Raises ValidationError on failure."""
    try:
        return schema.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc
