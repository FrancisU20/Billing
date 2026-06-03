"""
Gestión de usuarios por tenant.
Solo el admin del tenant y superadmin pueden gestionar usuarios.
"""
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.infrastructure.database.models.user import TenantUserModel, UserModel
from app.shared.dependencies import DbSession, TenantCtx

router = APIRouter()


class InviteUserRequest(BaseModel):
    email: str
    rol: str = "viewer"  # admin | operator | viewer
    cognito_sub: str  # el sub de Cognito se obtiene después de crear el usuario en Cognito


class UpdateRolRequest(BaseModel):
    rol: str


class UsuarioResponse(BaseModel):
    user_id: UUID
    cognito_sub: str
    email: str
    nombre: str | None
    rol: str
    estado: str

    model_config = {"from_attributes": True}


@router.get("/{tenant_id}/usuarios", response_model=list[UsuarioResponse])
async def list_usuarios(tenant_id: UUID, db: DbSession, ctx: TenantCtx):
    if not ctx.is_superadmin and str(tenant_id) != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    ctx.require_role("admin", "superadmin")

    result = await db.execute(
        select(TenantUserModel, UserModel)
        .join(UserModel, UserModel.id == TenantUserModel.user_id)
        .where(TenantUserModel.tenant_id == tenant_id, TenantUserModel.estado == "ACTIVE")
    )
    rows = result.all()
    return [
        UsuarioResponse(
            user_id=tu.user_id,
            cognito_sub=u.cognito_sub,
            email=u.email,
            nombre=u.nombre,
            rol=tu.rol,
            estado=tu.estado,
        )
        for tu, u in rows
    ]


@router.post("/{tenant_id}/usuarios", response_model=UsuarioResponse, status_code=201)
async def add_usuario(tenant_id: UUID, body: InviteUserRequest, db: DbSession, ctx: TenantCtx):
    """
    Asocia un usuario (ya existente en Cognito) a un tenant con un rol.
    El flujo de creación en Cognito es independiente (desde superadmin o AWS Console).
    """
    if not ctx.is_superadmin and str(tenant_id) != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    ctx.require_role("admin", "superadmin")

    # Crear o recuperar el usuario en la tabla users
    result = await db.execute(select(UserModel).where(UserModel.cognito_sub == body.cognito_sub))
    user = result.scalar_one_or_none()
    if not user:
        user = UserModel(cognito_sub=body.cognito_sub, email=body.email)
        db.add(user)
        await db.flush()

    # Verificar que no esté ya en el tenant
    existing = await db.execute(
        select(TenantUserModel).where(
            TenantUserModel.tenant_id == tenant_id,
            TenantUserModel.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="El usuario ya pertenece a este tenant")

    tu = TenantUserModel(tenant_id=tenant_id, user_id=user.id, rol=body.rol)
    db.add(tu)
    await db.flush()

    return UsuarioResponse(
        user_id=user.id,
        cognito_sub=user.cognito_sub,
        email=user.email,
        nombre=user.nombre,
        rol=tu.rol,
        estado=tu.estado,
    )


@router.patch("/{tenant_id}/usuarios/{user_id}", response_model=UsuarioResponse)
async def update_rol(tenant_id: UUID, user_id: UUID, body: UpdateRolRequest, db: DbSession, ctx: TenantCtx):
    if not ctx.is_superadmin and str(tenant_id) != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    result = await db.execute(
        select(TenantUserModel, UserModel)
        .join(UserModel, UserModel.id == TenantUserModel.user_id)
        .where(TenantUserModel.tenant_id == tenant_id, TenantUserModel.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado en este tenant")

    tu, u = row
    tu.rol = body.rol
    await db.flush()
    return UsuarioResponse(
        user_id=u.id, cognito_sub=u.cognito_sub, email=u.email,
        nombre=u.nombre, rol=tu.rol, estado=tu.estado,
    )


@router.delete("/{tenant_id}/usuarios/{user_id}", status_code=204)
async def remove_usuario(tenant_id: UUID, user_id: UUID, db: DbSession, ctx: TenantCtx):
    if not ctx.is_superadmin and str(tenant_id) != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    result = await db.execute(
        select(TenantUserModel).where(
            TenantUserModel.tenant_id == tenant_id,
            TenantUserModel.user_id == user_id,
        )
    )
    tu = result.scalar_one_or_none()
    if tu:
        tu.estado = "INACTIVE"
        await db.flush()
