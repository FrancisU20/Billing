from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.v1.deps import EstablecimientoRepo, PuntoEmisionRepo, SecuencialRepo
from app.shared.dependencies import TenantCtx

router = APIRouter()


class CreateEstablecimientoRequest(BaseModel):
    codigo: str
    direccion: str | None = None


class UpdateEstablecimientoRequest(BaseModel):
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
async def list_establecimientos(
    tenant_id: UUID, ctx: TenantCtx, est_repo: EstablecimientoRepo,
    include_inactive: bool = False,
):
    _check_access(ctx, tenant_id)
    return await est_repo.list_by_tenant(tenant_id, include_inactive=include_inactive)


@router.post("/{tenant_id}/establecimientos", response_model=EstablecimientoResponse, status_code=201)
async def create_establecimiento(
    tenant_id: UUID, body: CreateEstablecimientoRequest, ctx: TenantCtx, est_repo: EstablecimientoRepo
):
    _check_access(ctx, tenant_id)
    existing = await est_repo.get(tenant_id, body.codigo)
    if existing:
        raise HTTPException(status_code=409, detail=f"Establecimiento {body.codigo} ya existe")
    return await est_repo.create(tenant_id, body.codigo, body.direccion)


@router.patch("/{tenant_id}/establecimientos/{codigo}", response_model=EstablecimientoResponse)
async def update_establecimiento(
    tenant_id: UUID, codigo: str, body: UpdateEstablecimientoRequest,
    ctx: TenantCtx, est_repo: EstablecimientoRepo,
):
    _check_access(ctx, tenant_id)
    est = await est_repo.update(tenant_id, codigo, body.direccion)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    return est


@router.delete("/{tenant_id}/establecimientos/{codigo}", status_code=204)
async def delete_establecimiento(
    tenant_id: UUID, codigo: str, ctx: TenantCtx, est_repo: EstablecimientoRepo
):
    _check_access(ctx, tenant_id)
    await est_repo.delete(tenant_id, codigo)


@router.post("/{tenant_id}/establecimientos/{codigo}/activar", response_model=EstablecimientoResponse)
async def activate_establecimiento(
    tenant_id: UUID, codigo: str, ctx: TenantCtx, est_repo: EstablecimientoRepo
):
    _check_access(ctx, tenant_id)
    await est_repo.activate(tenant_id, codigo)
    est = await est_repo.get(tenant_id, codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    return est


# ── Puntos de emisión ─────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}/establecimientos/{codigo}/puntos-emision",
    response_model=list[PuntoEmisionResponse],
)
async def list_puntos_emision(
    tenant_id: UUID, codigo: str, ctx: TenantCtx,
    est_repo: EstablecimientoRepo, pto_repo: PuntoEmisionRepo,
    include_inactive: bool = False,
):
    _check_access(ctx, tenant_id)
    est = await est_repo.get(tenant_id, codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    return await pto_repo.list_by_establecimiento(est.id, include_inactive=include_inactive)


@router.post(
    "/{tenant_id}/establecimientos/{codigo}/puntos-emision",
    response_model=PuntoEmisionResponse,
    status_code=201,
)
async def create_punto_emision(
    tenant_id: UUID, codigo: str, body: CreatePuntoEmisionRequest,
    ctx: TenantCtx, est_repo: EstablecimientoRepo, pto_repo: PuntoEmisionRepo,
):
    _check_access(ctx, tenant_id)
    est = await est_repo.get(tenant_id, codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    existing = await pto_repo.get(est.id, body.codigo)
    if existing:
        raise HTTPException(status_code=409, detail=f"Punto de emisión {body.codigo} ya existe")
    return await pto_repo.create(est.id, body.codigo)


@router.delete(
    "/{tenant_id}/establecimientos/{est_codigo}/puntos-emision/{pto_codigo}",
    status_code=204,
)
async def delete_punto_emision(
    tenant_id: UUID, est_codigo: str, pto_codigo: str,
    ctx: TenantCtx, est_repo: EstablecimientoRepo, pto_repo: PuntoEmisionRepo,
):
    _check_access(ctx, tenant_id)
    est = await est_repo.get(tenant_id, est_codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    await pto_repo.delete(est.id, pto_codigo)


@router.post(
    "/{tenant_id}/establecimientos/{est_codigo}/puntos-emision/{pto_codigo}/activar",
    response_model=PuntoEmisionResponse,
)
async def activate_punto_emision(
    tenant_id: UUID, est_codigo: str, pto_codigo: str,
    ctx: TenantCtx, est_repo: EstablecimientoRepo, pto_repo: PuntoEmisionRepo,
):
    _check_access(ctx, tenant_id)
    est = await est_repo.get(tenant_id, est_codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    await pto_repo.activate(est.id, pto_codigo)
    pto = await pto_repo.get(est.id, pto_codigo)
    if not pto:
        raise HTTPException(status_code=404, detail="Punto de emisión no encontrado")
    return pto


# ── Secuenciales ──────────────────────────────────────────────────────────────

@router.get(
    "/{tenant_id}/establecimientos/{est_codigo}/puntos-emision/{pto_codigo}/secuenciales",
    response_model=list[SecuencialResponse],
)
async def list_secuenciales(
    tenant_id: UUID, est_codigo: str, pto_codigo: str, ctx: TenantCtx,
    est_repo: EstablecimientoRepo, pto_repo: PuntoEmisionRepo, sec_repo: SecuencialRepo,
):
    _check_access(ctx, tenant_id)
    est = await est_repo.get(tenant_id, est_codigo)
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    pto = await pto_repo.get(est.id, pto_codigo)
    if not pto:
        raise HTTPException(status_code=404, detail="Punto de emisión no encontrado")
    return await sec_repo.list_by_punto_emision(pto.id)
