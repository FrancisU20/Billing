from uuid import UUID
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.shared.dependencies import DbSession, TenantCtx
from app.infrastructure.database.models.user import UserModel, TenantUserModel

router = APIRouter()


class MeResponse(BaseModel):
    user_id: str
    email: str | None = None
    nombre: str | None = None
    tenant_id: str | None
    role: str
    is_superadmin: bool


@router.get("/me", response_model=MeResponse)
async def get_me(ctx: TenantCtx, db: DbSession):
    """Devuelve el perfil del usuario autenticado según el JWT."""
    result = await db.execute(
        select(UserModel).where(UserModel.cognito_sub == ctx.user_id)
    )
    user = result.scalar_one_or_none()
    return MeResponse(
        user_id=ctx.user_id or "",
        email=user.email if user else None,
        nombre=user.nombre if user else None,
        tenant_id=ctx.tenant_id,
        role=ctx.role,
        is_superadmin=ctx.is_superadmin,
    )
