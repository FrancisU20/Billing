"""
Construye eventos API Gateway HTTP API v2 a partir de requests HTTP locales.

También extrae path parameters de rutas conocidas para replicar
el comportamiento de API Gateway (ej. /tenants/abc-123 → {"id": "abc-123"}).
"""
from __future__ import annotations

import os
import re
import uuid
from typing import Any


# ── Patrones de extracción de path params ─────────────────────────────────────
# Orden: más específico primero

_PATH_PARAM_PATTERNS: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"^/tenants/([^/]+)/status$"), ["id"]),
    (re.compile(r"^/tenants/([^/]+)$"),        ["id"]),
    # Agregar patrones de nuevos Lambdas aquí:
    # (re.compile(r"^/clients/([^/]+)$"), ["id"]),
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
    Construye el evento en formato HTTP API Gateway v2.
    Los claims JWT se inyectan desde variables de entorno del .env local.
    En local nunca hay un JWT real — las credenciales vienen del .env.
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
