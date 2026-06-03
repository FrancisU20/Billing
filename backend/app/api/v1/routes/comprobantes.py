from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.api.v1.deps import (
    ComprobanteRepo,
    EstablecimientoRepo,
    PuntoEmisionRepo,
    SecuencialRepo,
    TenantRepo,
)
from app.application.use_cases.comprobantes.create_comprobante import (
    CreateComprobanteCommand,
    CreateComprobanteUseCase,
)
from app.application.use_cases.comprobantes.retry_comprobante import (
    RetryComprobanteCommand,
    RetryComprobanteUseCase,
)
from app.domain.enums.ambiente_sri import AmbienteSri
from app.infrastructure.storage.s3_storage import generar_presigned_url
from app.shared.dependencies import TenantCtx
from app.shared.exceptions import DomainError, NotFoundError, domain_error_to_http

router = APIRouter()


class CreateComprobanteRequest(BaseModel):
    tipo: str = "01"
    establecimiento: str
    punto_emision: str
    datos: dict
    idempotency_key: str | None = None
    external_reference: str | None = None


class RetryRequest(BaseModel):
    tipo: Literal["REENVIAR_SRI", "RECONSULTAR_AUTORIZACION", "REENVIAR_EMAIL"]


class ComprobanteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tipo: str
    clave_acceso: str | None
    establecimiento: str
    punto_emision: str
    secuencial: str | None
    estado: str
    idempotency_key: str | None
    external_reference: str | None
    numero_autorizacion: str | None
    retry_count: int
    error_detalle: str | None

    model_config = {"from_attributes": True}


@router.post("", response_model=ComprobanteResponse, status_code=202)
async def create_comprobante(
    body: CreateComprobanteRequest,
    ctx: TenantCtx,
    est_repo: EstablecimientoRepo,
    pto_repo: PuntoEmisionRepo,
    sec_repo: SecuencialRepo,
    comp_repo: ComprobanteRepo,
    tenant_repo: TenantRepo,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    tenant_id = UUID(ctx.require_tenant())
    idempotency = body.idempotency_key or x_idempotency_key

    est = await est_repo.get(tenant_id, body.establecimiento)
    if not est:
        raise HTTPException(
            status_code=422,
            detail=f"Establecimiento {body.establecimiento} no encontrado para este tenant",
        )
    pto = await pto_repo.get(est.id, body.punto_emision)
    if not pto:
        raise HTTPException(
            status_code=422,
            detail=f"Punto de emisión {body.punto_emision} no encontrado",
        )

    try:
        comp = await CreateComprobanteUseCase(comp_repo, tenant_repo, sec_repo).execute(
            CreateComprobanteCommand(
                tenant_id=tenant_id,
                tipo=body.tipo,
                establecimiento=body.establecimiento,
                punto_emision=body.punto_emision,
                punto_emision_id=pto.id,
                datos=body.datos,
                idempotency_key=idempotency,
                external_reference=body.external_reference,
            )
        )
        return ComprobanteResponse.model_validate(comp)
    except DomainError as e:
        raise domain_error_to_http(e) from e


@router.get("", response_model=dict)
async def list_comprobantes(
    ctx: TenantCtx,
    comp_repo: ComprobanteRepo,
    offset: int = 0,
    limit: int = 50,
    estado: str | None = None,
):
    tenant_id = UUID(ctx.require_tenant())
    comprobantes, total = await comp_repo.list_by_tenant(
        tenant_id, offset=offset, limit=limit, estado=estado
    )
    return {
        "items": [ComprobanteResponse.model_validate(c) for c in comprobantes],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{comprobante_id}", response_model=ComprobanteResponse)
async def get_comprobante(comprobante_id: UUID, ctx: TenantCtx, comp_repo: ComprobanteRepo):
    tenant_id = UUID(ctx.require_tenant())
    comp = await comp_repo.get_by_id(comprobante_id, tenant_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return ComprobanteResponse.model_validate(comp)


@router.patch("/{comprobante_id}/retry", response_model=ComprobanteResponse)
async def retry_comprobante(
    comprobante_id: UUID, body: RetryRequest,
    ctx: TenantCtx, comp_repo: ComprobanteRepo, tenant_repo: TenantRepo,
):
    tenant_id = UUID(ctx.require_tenant())
    tenant = await tenant_repo.get_by_id(tenant_id)
    ambiente = tenant.ambiente_sri if tenant else AmbienteSri.PRUEBAS

    try:
        comp = await RetryComprobanteUseCase(comp_repo).execute(
            RetryComprobanteCommand(
                comprobante_id=comprobante_id,
                tenant_id=tenant_id,
                tipo=body.tipo,
                ambiente=ambiente,
            )
        )
        return ComprobanteResponse.model_validate(comp)
    except (DomainError, NotFoundError) as e:
        raise domain_error_to_http(e) from e


@router.get("/{comprobante_id}/descargar/xml")
async def descargar_xml(comprobante_id: UUID, ctx: TenantCtx, comp_repo: ComprobanteRepo):
    tenant_id = UUID(ctx.require_tenant())
    comp = await comp_repo.get_by_id(comprobante_id, tenant_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    s3_key = comp.s3_key_xml_autorizado or comp.s3_key_xml_firmado
    if not s3_key:
        raise HTTPException(status_code=404, detail="XML no disponible aún")

    url = generar_presigned_url(s3_key, expires_in=900)
    return {"url": url, "expires_in": 900}


@router.get("/{comprobante_id}/descargar/pdf")
async def descargar_pdf(comprobante_id: UUID, ctx: TenantCtx, comp_repo: ComprobanteRepo):
    tenant_id = UUID(ctx.require_tenant())
    comp = await comp_repo.get_by_id(comprobante_id, tenant_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if not comp.s3_key_pdf:
        raise HTTPException(status_code=404, detail="PDF no disponible aún")

    url = generar_presigned_url(comp.s3_key_pdf, expires_in=900)
    return {"url": url, "expires_in": 900}
