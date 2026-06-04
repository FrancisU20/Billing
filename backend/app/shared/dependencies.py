from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import get_session_factory
from app.shared.config import get_settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session, session.begin():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def _claims_from_bearer(request: Request) -> dict:
    """En local, decodifica el JWT del header Authorization sin verificar firma.
    En producción el Lambda Authorizer ya verificó — aquí solo leemos claims."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return {}
    try:
        return jwt.get_unverified_claims(auth.removeprefix("Bearer ").strip())
    except Exception:
        return {}


class TenantContext:
    def __init__(
        self,
        request: Request,
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    ):
        apigw_context = (request.scope.get("aws.event") or {}).get("requestContext", {}).get("authorizer", {})
        settings = get_settings()

        if apigw_context:
            # Producción: claims inyectados por el Lambda Authorizer
            tenant_from_jwt = apigw_context.get("tenant_id")
            self.tenant_id: str | None = tenant_from_jwt or None
            self.user_id: str | None = apigw_context.get("user_id")
            self.role: str = apigw_context.get("role", "viewer")
            self.is_superadmin: bool = apigw_context.get("is_superadmin", "false").lower() == "true"
        elif settings.is_local:
            # Local: decodificar el JWT del Bearer token (sin verificar firma)
            claims = _claims_from_bearer(request)
            self.tenant_id = claims.get("custom:tenant_id") or x_tenant_id
            self.user_id = claims.get("sub")
            self.role = claims.get("custom:role", "viewer")
            self.is_superadmin = claims.get("custom:is_superadmin") in ("true", True)
        else:
            self.tenant_id = None
            self.user_id = None
            self.role = "viewer"
            self.is_superadmin = False

    def require_superadmin(self) -> None:
        if not self.is_superadmin:
            raise HTTPException(status_code=403, detail="Se requiere rol superadmin")

    def require_tenant(self) -> str:
        if not self.tenant_id:
            raise HTTPException(status_code=403, detail="tenant_id requerido")
        return self.tenant_id

    def require_role(self, *roles: str) -> None:
        if self.role not in roles and not self.is_superadmin:
            raise HTTPException(status_code=403, detail=f"Se requiere uno de los roles: {roles}")


TenantCtx = Annotated[TenantContext, Depends(TenantContext)]
