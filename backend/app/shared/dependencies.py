from typing import Annotated, AsyncGenerator
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.connection import get_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        async with session.begin():
            yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


class TenantContext:
    def __init__(
        self,
        request: Request,
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    ):
        # En producción, el Lambda Authorizer inyecta el contexto via requestContext
        # En local, se acepta X-Tenant-Id para desarrollo
        apigw_context = (request.scope.get("aws.event") or {}).get("requestContext", {}).get("authorizer", {})

        self.tenant_id: str | None = apigw_context.get("tenant_id") or x_tenant_id
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
