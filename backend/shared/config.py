"""
Helpers to read environment variables.

Usage pattern in each Lambda handler.py (outside the handler, at cold start):

    from shared.config import env, ENV, LOG_LEVEL

    _TABLE  = env("TENANTS_TABLE")          # required — fails at cold start if missing
    _QUEUE  = env("EVENTS_QUEUE_URL", "")   # optional

Each Lambda declares only the variables it actually uses.
There is no global Config object holding all tables — that would force every Lambda
to carry env vars it does not need and violates the least-privilege principle.
"""
from __future__ import annotations

import os


def env(name: str, default: str | None = None) -> str:
    """
    Read an environment variable. If `default` is None and the variable does
    not exist, raises RuntimeError immediately (cold start fail-fast).
    """
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(
            f"Required environment variable not set: {name}"
        )
    return value


# ── Truly global variables (present in all Lambdas) ───────────────────────────

ENV       = env("ENV",        "dev")
LOG_LEVEL = env("LOG_LEVEL",  "INFO")
REGION    = env("AWS_REGION", "sa-east-1")
