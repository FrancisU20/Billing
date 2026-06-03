from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.database.repositories.establecimiento_repository import (
    EstablecimientoRepository,
    PuntoEmisionRepository,
)
from app.shared.dependencies import DbSession, TenantCtx

router = APIRouter()


class CreateEstablecimientoRequest(BaseModel):
    codigo: str
    direccion: str | None = None


class CreatePuntoEmisionRequest(BaseModel):
    codigo: str


class EstablecimientoResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    codigo: str
    direccion: str | None
    estado: str
    model_config = {"from_attributes": True}


class PuntoEmisionResponse(BaseModel):
    id: UUID
    establecimiento_id: UUID
    codigo: str
    estado: str
    model_config = {"from_attributes": True}


class SecuencialResponse(BaseModel):
    punto_emision_id: UUID
    tipo_comprobante: str
    secuencial_actual: int
    model_config = {"from_attributes": True}


def _check_access(ctx: TenantCtx, tenant_id: UUID) -> None:
    if not ctx.is_superadmin and str(tenant_id) != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")


# ── Establecimientos ──────────────────────────────────────────────────────────

@router.get("/{tenant_id}/establecimientos", response_model=list[EstablecimientoResponse])
async def list_establecimientos(tenant_id: UUID, db: DbSession, ctx: TenantCtx):
    _check_access(ctx, tenant_id)
    return await EstablecimientoRepository(db).list_by_tenant(tenant_id)


@router.post("/{tenant_id}/establecimientos", response_model=EstablecimientoResponse, status_code=201)
async def create_establecimiento(
    tenant_id: UUID, body: CreateEstablecimientoRequest, db: DbSession, ctx: TenantCtx
):
    _check_access(ctx, tenant_id)
    existing = await EstablecimientoRepository(db).get(tenant_id, body.codigo)
    if existing:
        raise HTTPException(status_code=409, detail=f"Establecimiento {body.codigo} ya existe")
    return await EstablecimientoRepository(db).create(tenant_id, body.codigo, body.direccion)


@router.delete("/{tenant_id}/establecimientos/{codigo}", status_code=204)
async def delete_establecimiento(tenant_id: UUID, codigo: str, db: DbSession, ctx: TenantCtx):
    _check_access(ctx, tenant_id)
    await EstablecimientoRepository(db).delete(tenant_id, codigo)


# ── Puntos de emisión ─────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}/establecimientos/{codigo}/puntos-emision",
    response_model=list[PuntoEmisionResponse],
)
async def list_puntos_emision(tenant_id: UUID, codigo: str, db: DbSession, ctx: TenantCtx):
    _check_access(ctx, tenant_id)
    est = await EstablecimientoRepository(db).get(tenant_id, codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    return await PuntoEmisionRepository(db).list_by_establecimiento(est.id)


@router.post(
    "/{tenant_id}/establecimientos/{codigo}/puntos-emision",
    response_model=PuntoEmisionResponse,
    status_code=201,
)
async def create_punto_emision(
    tenant_id: UUID, codigo: str, body: CreatePuntoEmisionRequest, db: DbSession, ctx: TenantCtx
):
    _check_access(ctx, tenant_id)
    est = await EstablecimientoRepository(db).get(tenant_id, codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    existing = await PuntoEmisionRepository(db).get(est.id, body.codigo)
    if existing:
        raise HTTPException(status_code=409, detail=f"Punto de emisión {body.codigo} ya existe")
    return await PuntoEmisionRepository(db).create(est.id, body.codigo)


# ── Secuenciales ──────────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}/establecimientos/{est_codigo}/puntos-emision/{pto_codigo}/secuenciales",
    response_model=list[SecuencialResponse],
)
async def list_secuenciales(
    tenant_id: UUID, est_codigo: str, pto_codigo: str, db: DbSession, ctx: TenantCtx
):
    _check_access(ctx, tenant_id)
    est = await EstablecimientoRepository(db).get(tenant_id, est_codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    pto = await PuntoEmisionRepository(db).get(est.id, pto_codigo)
    if not pto:
        raise HTTPException(status_code=404, detail="Punto de emisión no encontrado")
    from sqlalchemy import select

    from app.infrastructure.database.models.establecimiento import SecuencialModel
    result = await db.execute(
        select(SecuencialModel).where(SecuencialModel.punto_emision_id == pto.id)
    )
    return list(result.scalars().all())
