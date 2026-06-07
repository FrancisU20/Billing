"""
Helpers para leer variables de entorno.

Patrón de uso en cada Lambda handler.py (fuera del handler, en cold start):

    from shared.config import env, ENV, LOG_LEVEL

    _TABLE  = env("TENANTS_TABLE")          # requerida — falla en cold start si falta
    _QUEUE  = env("EVENTS_QUEUE_URL", "")   # opcional

Cada Lambda solo declara las variables que realmente usa.
No existe un objeto Config global con todas las tablas — eso obligaría a cada Lambda
a tener env vars que no le corresponden y viola el principio de mínimo privilegio.
"""
from __future__ import annotations

import os


def env(name: str, default: str | None = None) -> str:
    """
    Lee una variable de entorno. Si `default` es None y la variable no existe,
    lanza RuntimeError inmediatamente (cold start fail-fast).
    """
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(
            f"Variable de entorno requerida no configurada: {name}"
        )
    return value


# ── Variables verdaderamente globales (presentes en todos los Lambdas) ────────

ENV       = env("ENV",        "dev")
LOG_LEVEL = env("LOG_LEVEL",  "INFO")
REGION    = env("AWS_REGION", "sa-east-1")
