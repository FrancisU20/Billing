import re
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.api.v1.deps import TenantRepo
from app.application.use_cases.tenants.create_tenant import CreateTenantCommand, CreateTenantUseCase
from app.application.use_cases.tenants.get_tenant import GetTenantUseCase, ListTenantsUseCase
from app.application.use_cases.tenants.update_tenant import UpdateTenantCommand, UpdateTenantUseCase
from app.domain.enums.ambiente_sri import AmbienteSri
from app.shared.dependencies import TenantCtx
from app.shared.exceptions import DomainError, NotFoundError, domain_error_to_http

router = APIRouter()


class CreateTenantRequest(BaseModel):
    ruc: str
    razon_social: str
    admin_email: str
    nombre_comercial: str | None = None
    ambiente_sri: AmbienteSri = AmbienteSri.PRUEBAS

    @field_validator("ruc")
    @classmethod
    def validate_ruc(cls, v: str) -> str:
        if not re.fullmatch(r"\d{13}", v):
            raise ValueError("RUC debe tener exactamente 13 dígitos")
        return v

    @field_validator("admin_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("Correo electrónico inválido")
        return v.lower()


class UpdateTenantRequest(BaseModel):
    razon_social: str | None = None
    nombre_comercial: str | None = None
    ambiente_sri: AmbienteSri | None = None
    estado: str | None = None


class TenantResponse(BaseModel):
    id: UUID
    ruc: str
    razon_social: str
    nombre_comercial: str | None
    estado: str
    ambiente_sri: str
    comprobantes_mes_actual: int

    model_config = {"from_attributes": True}


@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(body: CreateTenantRequest, ctx: TenantCtx, repo: TenantRepo):
    ctx.require_superadmin()
    try:
        tenant = await CreateTenantUseCase(repo).execute(
            CreateTenantCommand(
                ruc=body.ruc,
                razon_social=body.razon_social,
                admin_email=str(body.admin_email),
                nombre_comercial=body.nombre_comercial,
                ambiente_sri=body.ambiente_sri,
            )
        )
        return TenantResponse.model_validate(tenant)
    except DomainError as e:
        raise domain_error_to_http(e) from e


@router.get("", response_model=list[TenantResponse])
async def list_tenants(ctx: TenantCtx, repo: TenantRepo, offset: int = 0, limit: int = 50):
    ctx.require_superadmin()
    tenants = await ListTenantsUseCase(repo).execute(offset=offset, limit=limit)
    return [TenantResponse.model_validate(t) for t in tenants]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: UUID, ctx: TenantCtx, repo: TenantRepo):
    if not ctx.is_superadmin and str(tenant_id) != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    try:
        tenant = await GetTenantUseCase(repo).execute(tenant_id)
        return TenantResponse.model_validate(tenant)
    except NotFoundError as e:
        raise domain_error_to_http(e) from e


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: UUID, body: UpdateTenantRequest, ctx: TenantCtx, repo: TenantRepo):
    ctx.require_superadmin()
    try:
        tenant = await UpdateTenantUseCase(repo).execute(
            UpdateTenantCommand(
                tenant_id=tenant_id,
                razon_social=body.razon_social,
                nombre_comercial=body.nombre_comercial,
                ambiente_sri=body.ambiente_sri,
                estado=body.estado,
            )
        )
        return TenantResponse.model_validate(tenant)
    except (DomainError, NotFoundError) as e:
        raise domain_error_to_http(e) from e
