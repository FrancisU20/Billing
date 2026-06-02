"""
Endpoints de gestión de certificados de firma electrónica por tenant.

Flujo de carga:
  POST /tenants/{tenant_id}/certificates/upload-url  → obtener presigned URL de S3
  POST /tenants/{tenant_id}/certificates/confirm     → validar y registrar en Secrets Manager
  GET  /tenants/{tenant_id}/certificates             → listar certificados del tenant
"""
import uuid
from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.infrastructure.database.repositories.certificate_repository import CertificateRepository
from app.infrastructure.security.certificate_service import (
    generate_upload_url,
    validate_and_store_certificate,
)
from app.shared.dependencies import DbSession, TenantCtx

router = APIRouter()


class UploadUrlResponse(BaseModel):
    upload_url: str
    cert_id: str
    expires_in_seconds: int = 300


class ConfirmCertificateRequest(BaseModel):
    cert_id: str
    s3_key_upload: str
    password: str
    nombre: str | None = None


class CertificateResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    nombre: str | None
    fecha_emision: date | None
    fecha_expiracion: date | None
    estado: str

    model_config = {"from_attributes": True}


@router.post("/upload-url", response_model=UploadUrlResponse)
async def request_upload_url(tenant_id: UUID, ctx: TenantCtx):
    """
    Paso 1: genera una presigned URL de S3 para que el frontend suba el .p12 directamente.
    El archivo NUNCA pasa por el backend — va directo a S3 privado.
    """
    _require_tenant_access(ctx, tenant_id)
    cert_id = str(uuid.uuid4())
    upload_url, s3_key = generate_upload_url(str(tenant_id), cert_id, expires_in=300)
    return UploadUrlResponse(upload_url=upload_url, cert_id=cert_id)


@router.post("/confirm", response_model=CertificateResponse, status_code=201)
async def confirm_certificate(tenant_id: UUID, body: ConfirmCertificateRequest, db: DbSession, ctx: TenantCtx):
    """
    Paso 2: valida el .p12, guarda la contraseña en Secrets Manager y registra el certificado.
    La contraseña NO se almacena en la DB — solo el ARN del secret.
    """
    _require_tenant_access(ctx, tenant_id)
    try:
        metadata = validate_and_store_certificate(
            tenant_id=str(tenant_id),
            cert_id=body.cert_id,
            s3_key_upload=body.s3_key_upload,
            password=body.password,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    cert_repo = CertificateRepository(db)
    cert = await cert_repo.create(
        tenant_id=tenant_id,
        nombre=body.nombre,
        s3_key=metadata["s3_key"],
        secrets_manager_arn=metadata["secrets_manager_arn"],
        fecha_emision=metadata["fecha_emision"],
        fecha_expiracion=metadata["fecha_expiracion"],
    )
    return CertificateResponse.model_validate(cert)


@router.get("", response_model=list[CertificateResponse])
async def list_certificates(tenant_id: UUID, db: DbSession, ctx: TenantCtx):
    _require_tenant_access(ctx, tenant_id)
    certs = await CertificateRepository(db).list_for_tenant(tenant_id)
    return [CertificateResponse.model_validate(c) for c in certs]


def _require_tenant_access(ctx: TenantCtx, tenant_id: UUID) -> None:
    if not ctx.is_superadmin and str(tenant_id) != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Acceso denegado a este tenant")
