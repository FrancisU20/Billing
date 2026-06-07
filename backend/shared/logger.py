"""
Structured JSON logger with per-invocation context propagation.

Problem solved: `bind()` in the handler must appear in logs from ALL modules
(use_cases, repositories, etc.) without passing the context manually.

Solution: `contextvars.ContextVar` — context is per execution, not global.
In Lambda (synchronous execution) each invocation has its own context,
initialized in the @lambda_handler decorator.

Usage:
    from shared.logger import get_logger
    _log = get_logger(__name__)
    _log.info("tenant created", tenant_id="t-123")   # request_id appears automatically

To propagate context from the handler (@lambda_handler does this automatically):
    from shared.logger import bind_invocation_context
    bind_invocation_context(request_id="...", tenant_id="...", user_id="...")
"""
import json
import logging
import os
import traceback as tb
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any


_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Per-invocation context — propagated to all loggers automatically
_invocation_ctx: ContextVar[dict[str, Any]] = ContextVar(
    "invocation_ctx", default={}
)


def bind_invocation_context(**kwargs: Any) -> None:
    """Bind fields to the current invocation context (request_id, tenant_id, etc.)."""
    _invocation_ctx.set({**_invocation_ctx.get(), **kwargs})


def clear_invocation_context() -> None:
    """Clear the context at the start of each Lambda invocation."""
    _invocation_ctx.set({})


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self._name = name
        self._ctx: dict[str, Any] = {}
        self._logger = logging.getLogger(name)
        self._logger.setLevel(getattr(logging, _LOG_LEVEL, logging.INFO))
        if not self._logger.handlers:
            _h = logging.StreamHandler()
            _h.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(_h)
            self._logger.propagate = False

    def bind(self, **kwargs: Any) -> None:
        """Add permanent fields to THIS logger (not propagated to other modules)."""
        self._ctx.update(kwargs)

    def _emit(self, level: str, message: str, **extra: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     level,
            "logger":    self._name,
            "message":   message,
            **_invocation_ctx.get(),   # invocation context (request_id, tenant_id…)
            **self._ctx,               # fixed context of this logger
            **extra,                   # extra fields from the caller
        }
        self._logger.log(
            getattr(logging, level.upper(), logging.INFO),
            json.dumps(record, default=str),
        )

    def debug(self, msg: str, **kw: Any) -> None:
        self._emit("debug", msg, **kw)

    def info(self, msg: str, **kw: Any) -> None:
        self._emit("info", msg, **kw)

    def warning(self, msg: str, **kw: Any) -> None:
        self._emit("warning", msg, **kw)

    def error(self, msg: str, exc_info: bool = False, **kw: Any) -> None:
        if exc_info:
            kw["traceback"] = tb.format_exc()
        self._emit("error", msg, **kw)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
