"""
Middleware que simula el Lambda Authorizer de API Gateway en entorno local.

En producción:
  Request → API Gateway → Lambda Authorizer (verifica JWT, extrae claims)
          → inyecta requestContext.authorizer → FastAPI → TenantContext

En local:
  Request → uvicorn → LocalAuthMiddleware (misma lógica: verifica JWT, extrae claims)
          → inyecta request.scope["aws.event"]["requestContext"]["authorizer"]
          → FastAPI → TenantContext  ← sin cambios, lee del mismo lugar

El middleware usa _verify_token() del authorizer real — misma verificación
JWKS + RS256. El comportamiento es funcionalmente idéntico a producción.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.shared.logging import logger
from lambda_handlers.authorizer_handler import _verify_token


class LocalAuthMiddleware(BaseHTTPMiddleware):
    """Simula el Lambda Authorizer de API Gateway para desarrollo local."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            try:
                claims = _verify_token(token)
                self._inject_authorizer_context(request, claims)
            except Exception as exc:
                logger.debug("LocalAuthMiddleware: token inválido o expirado", extra={"error": str(exc)})

        return await call_next(request)

    @staticmethod
    def _inject_authorizer_context(request: Request, claims: dict) -> None:
        """Inyecta el mismo contexto que produciría el Lambda Authorizer real."""
        is_superadmin = claims.get("custom:is_superadmin") in ("true", True)
        tenant_id = claims.get("custom:tenant_id") or ""

        authorizer_context = {
            "tenant_id": tenant_id,
            "user_id": claims.get("sub", ""),
            "role": claims.get("custom:role", "viewer"),
            "is_superadmin": "true" if is_superadmin else "false",
        }

        if "aws.event" not in request.scope:
            request.scope["aws.event"] = {}

        request.scope["aws.event"].setdefault("requestContext", {})["authorizer"] = authorizer_context
