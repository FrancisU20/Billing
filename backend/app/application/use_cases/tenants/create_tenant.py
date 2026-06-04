import json
import os
from dataclasses import dataclass

import boto3
from aws_lambda_powertools import Logger

from app.domain.entities.tenant import Tenant
from app.domain.enums.ambiente_sri import AmbienteSri
from app.domain.repositories.tenant_repository import TenantRepository
from app.infrastructure.cognito.user_service import CognitoUserService
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
    def __init__(
        self,
        tenant_repo: TenantRepository,
        cognito_service: CognitoUserService,
    ) -> None:
        self._repo = tenant_repo
        self._cognito = cognito_service

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

        # Crear usuario admin en Cognito (síncrono — necesitamos la contraseña)
        temp_password = self._cognito.create_tenant_admin(
            tenant_id=str(tenant.id),
            email=cmd.admin_email,
        )

        # Enviar email de bienvenida de forma asíncrona via SQS.
        # El email dispatch worker lo procesa sin bloquear la respuesta al superadmin.
        self._enqueue_welcome_email(
            email=cmd.admin_email,
            razon_social=cmd.razon_social,
            temp_password=temp_password,
        )

        return tenant

    def _enqueue_welcome_email(
        self, email: str, razon_social: str, temp_password: str
    ) -> None:
        settings = get_settings()
        if not settings.sqs_email_dispatch_url:
            logger.warning("SQS email dispatch URL not configured — skipping welcome email")
            return

        try:
            sqs = boto3.client("sqs", region_name=os.environ.get("AWS_REGION_NAME", "sa-east-1"))
            sqs.send_message(
                QueueUrl=settings.sqs_email_dispatch_url,
                MessageBody=json.dumps({
                    "type": "WELCOME",
                    "email": email,
                    "razon_social": razon_social,
                    "temp_password": temp_password,
                }),
            )
            logger.info("Welcome email enqueued", extra={"email": email})
        except Exception as exc:
            # El email es best-effort — no debe fallar la creación del tenant
            logger.error("Failed to enqueue welcome email", extra={"error": str(exc), "email": email})
