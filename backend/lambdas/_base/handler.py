"""
Decorator @lambda_handler para Lambdas HTTP (API Gateway).

Responsabilidades:
1. Limpia el contexto de la invocación anterior (importante en containers reutilizados)
2. Parsea el event de API Gateway → objeto Request
3. Propaga request_id, tenant_id, user_id a TODOS los loggers vía contextvars
4. Ejecuta la función del Lambda
5. Captura AppError → devuelve ApiResponse.error con el código correcto
6. Captura Exception genérica → loguea stacktrace completo → InternalError al cliente
   (el stacktrace NUNCA viaja al HTTP response, solo a CloudWatch)

Uso:
    from lambdas._base.handler import lambda_handler

    @lambda_handler
    def handler(request: Request, context) -> dict:
        ...
        return ApiResponse.ok(data, request.request_id)
"""
import functools
from typing import Callable

from lambdas._base.parser import Request
from lambdas._base.response import ApiResponse
from shared.errors import AppError, InternalError
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)


def lambda_handler(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(event: dict, context) -> dict:
        clear_invocation_context()

        request_id = (
            event.get("requestContext", {}).get("requestId", "local")
        )
        try:
            request = Request.from_event(event)
            bind_invocation_context(
                request_id  = request_id,
                tenant_id   = request.tenant_id,
                user_id     = request.user_id,
                lambda_name = getattr(context, "function_name", "local"),
            )
            _log.info("request recibido")
            result = func(request, context)
            _log.info("request completado")
            return result

        except AppError as exc:
            _log.warning("error de aplicación", code=exc.code, detail=exc.detail)
            return ApiResponse.error(exc, request_id)

        except Exception:
            _log.error("error inesperado", exc_info=True)
            return ApiResponse.error(InternalError(), request_id)

    return wrapper
