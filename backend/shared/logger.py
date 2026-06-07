"""
Logger estructurado JSON con propagación de contexto por invocación.

Problema resuelto: `bind()` en el handler debe aparecer en logs de TODOS los módulos
(use_cases, repositorios, etc.) sin pasarles el contexto manualmente.

Solución: `contextvars.ContextVar` — el contexto es por ejecución, no global.
En Lambda (ejecución síncrona), cada invocación tiene su propio contexto
que se inicializa en el decorator @lambda_handler.

Uso:
    from shared.logger import get_logger
    _log = get_logger(__name__)
    _log.info("tenant creado", tenant_id="t-123")   # request_id aparece automáticamente

Para propagar contexto desde el handler (lo hace @lambda_handler automáticamente):
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

# Contexto por invocación — se propaga a todos los loggers automáticamente
_invocation_ctx: ContextVar[dict[str, Any]] = ContextVar(
    "invocation_ctx", default={}
)


def bind_invocation_context(**kwargs: Any) -> None:
    """Vincula campos al contexto de la invocación actual (request_id, tenant_id, etc.)."""
    _invocation_ctx.set({**_invocation_ctx.get(), **kwargs})


def clear_invocation_context() -> None:
    """Limpia el contexto al inicio de cada invocación Lambda."""
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
        """Agrega campos permanentes a ESTE logger (no se propaga a otros módulos)."""
        self._ctx.update(kwargs)

    def _emit(self, level: str, message: str, **extra: Any) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     level,
            "logger":    self._name,
            "message":   message,
            **_invocation_ctx.get(),   # contexto de invocación (request_id, tenant_id…)
            **self._ctx,               # contexto fijo de este logger
            **extra,                   # campos extra del llamante
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
