import json
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Logger

from app.domain.entities.tenant import Tenant
from app.domain.enums.ambiente_sri import AmbienteSri
from app.domain.repositories.tenant_repository import TenantRepository
from app.shared.config import get_settings
from app.shared.exceptions import DomainError

logger = Logger(service="codelabs-billing-create-tenant")


@dataclass
class CreateTenantCommand:
    ruc: str
    razon_social: str
    admin_email: str
    nombre_comercial: str | None = None
    ambiente_sri: AmbienteSri = AmbienteSri.PRUEBAS
    plan_id: str | None = None


class CreateTenantUseCase:
    def __init__(self, tenant_repo: TenantRepository) -> None:
        self._repo = tenant_repo

    async def execute(self, cmd: CreateTenantCommand) -> Tenant:
        existing = await self._repo.get_by_ruc(cmd.ruc)
        if existing:
            raise DomainError(f"Ya existe un tenant con RUC {cmd.ruc}", code="TENANT_ALREADY_EXISTS")

        tenant = Tenant(
            ruc=cmd.ruc,
            razon_social=cmd.razon_social,
            nombre_comercial=cmd.nombre_comercial,
            ambiente_sri=cmd.ambiente_sri,
        )
        tenant = await self._repo.save(tenant)

        # Encolar onboarding — el worker crea el usuario en Cognito y envía el email.
        # La respuesta al superadmin es inmediata. El onboarding ocurre de forma asíncrona.
        self._enqueue_onboarding(tenant, cmd.admin_email)

        return tenant

    def _enqueue_onboarding(self, tenant: Tenant, admin_email: str) -> None:
        settings = get_settings()
        if not settings.sqs_tenant_onboarding_url:
            logger.warning("SQS tenant onboarding URL not configured — skipping")
            return

        try:
            sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION_NAME", "sa-east-1"))
            sqs.send_message(
                QueueUrl=settings.sqs_tenant_onboarding_url,
                MessageBody=json.dumps({
                    "tenant_id": str(tenant.id),
                    "ruc": tenant.ruc,
                    "razon_social": tenant.razon_social,
                    "admin_email": admin_email,
                }),
            )
            logger.info("Tenant onboarding enqueued", extra={"tenant_id": str(tenant.id)})
        except Exception as exc:
            logger.error("Failed to enqueue onboarding", extra={"error": str(exc), "tenant_id": str(tenant.id)})
