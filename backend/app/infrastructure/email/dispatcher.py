"""
Email dispatcher con fallback automático entre proveedores.
Orden: Brevo → Mailgun
"""
from app.infrastructure.email.provider import EmailMessage, EmailProvider
from app.shared.config import get_settings
from app.shared.logging import logger


def build_providers() -> list[EmailProvider]:
    from app.infrastructure.email.brevo_provider import BrevoEmailProvider
    from app.infrastructure.email.mailgun_provider import MailgunEmailProvider

    settings = get_settings()
    creds = settings.get_email_credentials()
    providers: list[EmailProvider] = []

    api_key = creds.get("api_key")
    if api_key:
        providers.append(BrevoEmailProvider(api_key=api_key))

    mailgun_key = creds.get("mailgun_api_key")
    mailgun_domain = creds.get("mailgun_domain")
    if mailgun_key and mailgun_domain:
        providers.append(MailgunEmailProvider(api_key=mailgun_key, domain=mailgun_domain))

    return providers


def dispatch(message: EmailMessage) -> str:
    """
    Intenta enviar el email con cada proveedor en orden.
    Retorna el nombre del proveedor que tuvo éxito.
    Lanza ValueError si todos fallan.
    """
    providers = build_providers()
    if not providers:
        raise ValueError("No hay proveedores de email configurados")

    for provider in providers:
        try:
            success = provider.send(message)
            if success:
                logger.info("Email sent", extra={"provider": provider.name, "to": message.to})
                return provider.name
        except Exception as e:
            logger.warning("Provider failed", extra={"provider": provider.name, "error": str(e)})
            continue

    raise ValueError(f"Todos los proveedores fallaron al enviar a {message.to}")
