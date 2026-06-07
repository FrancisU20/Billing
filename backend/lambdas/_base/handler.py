"""
@lambda_handler decorator for HTTP Lambdas (API Gateway).

Responsibilities:
1. Clears the previous invocation context (important in reused containers)
2. Parses the API Gateway event → Request object
3. Propagates request_id, tenant_id, user_id to ALL loggers via contextvars
4. Runs the Lambda function
5. Catches AppError → returns ApiResponse.error with the correct code
6. Catches generic Exception → logs full stacktrace → InternalError to the client
   (the stacktrace NEVER travels to the HTTP response, only to CloudWatch)

Usage:
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
            _log.info("request received")
            result = func(request, context)
            _log.info("request completed")
            return result

        except AppError as exc:
            _log.warning("application error", code=exc.code, detail=exc.detail)
            return ApiResponse.error(exc, request_id)

        except Exception:
            _log.error("unexpected error", exc_info=True)
            return ApiResponse.error(InternalError(), request_id)

    return wrapper
