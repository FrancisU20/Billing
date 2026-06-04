"""
Worker de onboarding de nuevos tenants.

Flujo:
1. Recibe evento SQS con tenant_id, razon_social y admin_email
2. Crea el usuario admin en Cognito (AdminCreateUser + AdminSetUserPassword)
3. Envía el email de bienvenida con las credenciales via Brevo SMTP

Separado del API Lambda para no bloquear la respuesta al superadmin.
Si Cognito falla, SQS reintenta automáticamente (hasta max_receive_count).
"""
from aws_lambda_powertools import Logger

from app.infrastructure.cognito.user_service import CognitoUserService
from app.infrastructure.email.brevo_provider import BrevoEmailProvider
from app.infrastructure.email.provider import EmailMessage
from app.shared.config import get_settings

logger = Logger(service="codelabs-billing-tenant-onboarding")


async def procesar_onboarding(tenant_id: str, razon_social: str, admin_email: str) -> None:
    cognito = CognitoUserService()
    temp_password = cognito.create_tenant_admin(tenant_id=tenant_id, email=admin_email)
    logger.info("Cognito user created", extra={"tenant_id": tenant_id, "email": admin_email})

    _send_welcome_email(email=admin_email, razon_social=razon_social, temp_password=temp_password)


def _send_welcome_email(email: str, razon_social: str, temp_password: str) -> None:
    settings = get_settings()
    credentials = settings.get_email_credentials()
    api_key = credentials.get("api_key")

    if not api_key:
        logger.warning("Brevo API key not configured — skipping welcome email")
        return

    provider = BrevoEmailProvider(api_key=api_key)
    provider.send(EmailMessage(
        to=email,
        subject="Bienvenido a CodeLabs Billing — Tus credenciales de acceso",
        html_body=_welcome_html(razon_social, email, temp_password),
        from_name="CodeLabs Billing",
        from_email="noreply@codelabsecuador.com",
        attachments=[],
    ))
    logger.info("Welcome email sent", extra={"email": email})


def _welcome_html(razon_social: str, email: str, password: str) -> str:
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
