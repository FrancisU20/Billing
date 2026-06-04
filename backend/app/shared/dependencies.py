from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.connection import get_session_factory
from app.shared.config import get_settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session, session.begin():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


class TenantContext:
    def __init__(
        self,
        request: Request,
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    ):
        apigw_context = (request.scope.get("aws.event") or {}).get("requestContext", {}).get("authorizer", {})
        settings = get_settings()

        tenant_from_jwt = apigw_context.get("tenant_id")

        # X-Tenant-Id solo se acepta en ambiente local.
        # En cualquier otro ambiente el tenant_id debe venir del Lambda Authorizer.
        if tenant_from_jwt:
            self.tenant_id: str | None = tenant_from_jwt
        elif settings.is_local:
            self.tenant_id = x_tenant_id
        else:
            self.tenant_id = None

        self.user_id: str | None = apigw_context.get("user_id")
        self.role: str = apigw_context.get("role", "viewer")
        self.is_superadmin: bool = apigw_context.get("is_superadmin", "false").lower() == "true"

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
