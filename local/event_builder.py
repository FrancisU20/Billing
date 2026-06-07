"""
Builds API Gateway HTTP API v2 events from local HTTP requests.

Also extracts path parameters from known routes to replicate
API Gateway behavior (e.g. /tenants/abc-123 → {"id": "abc-123"}).
"""
from __future__ import annotations

import os
import re
import uuid
from typing import Any


# ── Path param extraction patterns ────────────────────────────────────────────
# Order: most specific first

_PATH_PARAM_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"^/tenants/([^/]+)/status$"), ["id"]),
    (re.compile(r"^/tenants/([^/]+)$"),        ["id"]),
    (re.compile(r"^/plans/([^/]+)/status$"),   ["id"]),
    (re.compile(r"^/plans/([^/]+)$"),          ["id"]),
]


def extract_path_params(path: str) -> dict[str, str]:
    for pattern, names in _PATH_PARAM_PATTERNS:
        m = pattern.match(path)
        if m:
            return dict(zip(names, m.groups()))
    return {}


def build_event(
    method:      str,
    path:        str,
    headers:     dict[str, str],
    query:       dict[str, str],
    body:        bytes,
) -> dict[str, Any]:
    """
    Builds the event in HTTP API Gateway v2 format.
    JWT claims are injected from the local .env environment variables.
    Locally there is never a real JWT — credentials come from .env.
    """
    claims: dict[str, str] = {
        "sub":                     os.environ.get("LOCAL_USER_ID",       "local-superadmin"),
        "email":                   os.environ.get("LOCAL_EMAIL",         "local@codelabs.com"),
        "custom:tenant_id":        os.environ.get("LOCAL_TENANT_ID",     ""),
        "custom:role":             os.environ.get("LOCAL_ROLE",          "superadmin"),
        "custom:is_superadmin":    os.environ.get("LOCAL_IS_SUPERADMIN", "true"),
    }

    return {
        "version":    "2.0",
        "routeKey":   f"{method} {path}",
        "rawPath":    path,
        "requestContext": {
            "requestId": str(uuid.uuid4()),
            "http": {
                "method":   method,
                "path":     path,
                "sourceIp": "127.0.0.1",
            },
            "authorizer": {
                "jwt": {"claims": claims}
            },
        },
        "headers":               {k.lower(): v for k, v in headers.items()},
        "queryStringParameters": query or None,
        "pathParameters":        extract_path_params(path) or None,
        "body":                  body.decode("utf-8") if body else None,
        "isBase64Encoded":       False,
    }
