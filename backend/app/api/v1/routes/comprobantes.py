from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.application.use_cases.comprobantes.create_comprobante import (
    CreateComprobanteCommand,
    CreateComprobanteUseCase,
)
from app.application.use_cases.comprobantes.retry_comprobante import (
    RetryComprobanteCommand,
    RetryComprobanteUseCase,
)
from app.infrastructure.database.repositories.comprobante_repository import SqlAlchemyComprobanteRepository
from app.infrastructure.database.repositories.tenant_repository import SqlAlchemyTenantRepository
from app.infrastructure.storage.s3_storage import generar_presigned_url
from app.shared.dependencies import DbSession, TenantCtx
from app.shared.exceptions import DomainError, NotFoundError, domain_error_to_http

router = APIRouter()


class CreateComprobanteRequest(BaseModel):
    tipo: str = "01"
    establecimiento: str
    punto_emision: str
    datos: dict
    idempotency_key: str | None = None
    external_reference: str | None = None
    # secuencial se auto-genera desde la DB — no enviar en el body


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
    db: DbSession,
    ctx: TenantCtx,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    tenant_id = UUID(ctx.require_tenant())
    idempotency = body.idempotency_key or x_idempotency_key

    comp_repo = SqlAlchemyComprobanteRepository(db)
    tenant_repo = SqlAlchemyTenantRepository(db)
    from app.infrastructure.database.repositories.establecimiento_repository import SecuencialRepository
    sec_repo = SecuencialRepository(db)

    try:
        comp = await CreateComprobanteUseCase(comp_repo, tenant_repo, sec_repo).execute(
            CreateComprobanteCommand(
                tenant_id=tenant_id,
                tipo=body.tipo,
                establecimiento=body.establecimiento,
                punto_emision=body.punto_emision,
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
    db: DbSession,
    ctx: TenantCtx,
    offset: int = 0,
    limit: int = 50,
    estado: str | None = None,
):
    tenant_id = UUID(ctx.require_tenant())
    comp_repo = SqlAlchemyComprobanteRepository(db)
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
async def get_comprobante(comprobante_id: UUID, db: DbSession, ctx: TenantCtx):
    tenant_id = UUID(ctx.require_tenant())
    comp_repo = SqlAlchemyComprobanteRepository(db)
    comp = await comp_repo.get_by_id(comprobante_id, tenant_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return ComprobanteResponse.model_validate(comp)


@router.patch("/{comprobante_id}/retry", response_model=ComprobanteResponse)
async def retry_comprobante(
    comprobante_id: UUID, body: RetryRequest, db: DbSession, ctx: TenantCtx
):
    tenant_id = UUID(ctx.require_tenant())
    comp_repo = SqlAlchemyComprobanteRepository(db)
    tenant_repo = SqlAlchemyTenantRepository(db)
    tenant = await tenant_repo.get_by_id(tenant_id)
    ambiente = tenant.ambiente_sri if tenant else "PRUEBAS"

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
async def descargar_xml(comprobante_id: UUID, db: DbSession, ctx: TenantCtx):
    """Genera presigned URL para descargar el XML autorizado."""
    tenant_id = UUID(ctx.require_tenant())
    comp_repo = SqlAlchemyComprobanteRepository(db)
    comp = await comp_repo.get_by_id(comprobante_id, tenant_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    s3_key = comp.s3_key_xml_autorizado or comp.s3_key_xml_firmado
    if not s3_key:
        raise HTTPException(status_code=404, detail="XML no disponible aún")

    url = generar_presigned_url(s3_key, expires_in=900)
    return {"url": url, "expires_in": 900}


@router.get("/{comprobante_id}/descargar/pdf")
async def descargar_pdf(comprobante_id: UUID, db: DbSession, ctx: TenantCtx):
    """Genera presigned URL para descargar el PDF/RIDE."""
    tenant_id = UUID(ctx.require_tenant())
    comp_repo = SqlAlchemyComprobanteRepository(db)
    comp = await comp_repo.get_by_id(comprobante_id, tenant_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    if not comp.s3_key_pdf:
        raise HTTPException(status_code=404, detail="PDF no disponible aún")

    url = generar_presigned_url(comp.s3_key_pdf, expires_in=900)
    return {"url": url, "expires_in": 900}
