from fastapi import APIRouter
from pydantic import BaseModel

from app.api.v1.deps import UserRepo
from app.shared.dependencies import TenantCtx

router = APIRouter()


class MeResponse(BaseModel):
    user_id: str
    email: str | None = None
    nombre: str | None = None
    tenant_id: str | None
    role: str
    is_superadmin: bool


@router.get("/me", response_model=MeResponse)
async def get_me(ctx: TenantCtx, user_repo: UserRepo):
    """Devuelve el perfil del usuario autenticado según el JWT."""
    user = await user_repo.get_by_cognito_sub(ctx.user_id or "")
    return MeResponse(
        user_id=ctx.user_id or "",
        email=user.email if user else None,
        nombre=user.nombre if user else None,
        tenant_id=ctx.tenant_id,
        role=ctx.role,
        is_superadmin=ctx.is_superadmin,
    )
