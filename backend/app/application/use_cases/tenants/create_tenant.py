from dataclasses import dataclass

from aws_lambda_powertools import Logger

from app.domain.entities.tenant import Tenant
from app.domain.enums.ambiente_sri import AmbienteSri
from app.domain.repositories.tenant_repository import TenantRepository
from app.infrastructure.cognito.user_service import CognitoUserService
from app.infrastructure.email.brevo_provider import BrevoEmailProvider
from app.infrastructure.email.provider import EmailMessage
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

        # Crear usuario admin en Cognito
        temp_password = self._cognito.create_tenant_admin(
            tenant_id=str(tenant.id),
            email=cmd.admin_email,
        )

        # Enviar email de bienvenida con credenciales
        self._send_welcome_email(
            email=cmd.admin_email,
            razon_social=cmd.razon_social,
            temp_password=temp_password,
        )

        return tenant

    def _send_welcome_email(self, email: str, razon_social: str, temp_password: str) -> None:
        settings = get_settings()
        credentials = settings.get_email_credentials()
        if not credentials.get("api_key"):
            logger.warning("Email credentials not configured — skipping welcome email")
            return

        try:
            provider = BrevoEmailProvider(api_key=credentials["api_key"])
            provider.send(EmailMessage(
                to=email,
                subject="Bienvenido a CodeLabs Billing — Tus credenciales de acceso",
                html_body=_welcome_email_html(razon_social, email, temp_password),
                from_name="CodeLabs Billing",
                from_email="noreply@codelabsecuador.com",
                attachments=[],
            ))
            logger.info("Welcome email sent", extra={"email": email})
        except Exception as exc:
            logger.error("Failed to send welcome email", extra={"error": str(exc), "email": email})


def _welcome_email_html(razon_social: str, email: str, password: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto">
      <h2 style="color:#1a56db">Bienvenido a CodeLabs Billing</h2>
      <p>Hola, tu empresa <strong>{razon_social}</strong> ha sido registrada en CodeLabs Billing Cloud.</p>
      <p>Tus credenciales de acceso son:</p>
      <table style="border-collapse:collapse;width:100%;margin:16px 0">
        <tr style="background:#f3f4f6">
          <td style="padding:10px;font-weight:bold;width:140px">Correo</td>
          <td style="padding:10px;font-family:monospace">{email}</td>
        </tr>
        <tr>
          <td style="padding:10px;font-weight:bold">Contraseña</td>
          <td style="padding:10px;font-family:monospace;font-size:16px">{password}</td>
        </tr>
      </table>
      <p>Accede en: <a href="https://billing-dev.codelabsecuador.com">billing-dev.codelabsecuador.com</a></p>
      <p style="color:#666;font-size:12px">Te recomendamos cambiar tu contraseña en la primera sesión.</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
      <p style="color:#999;font-size:11px">CodeLabs Billing Cloud — Sistema de Facturación Electrónica Ecuador</p>
    </body></html>
    """
