import base64

import brevo
from brevo.rest import ApiException

from app.infrastructure.email.provider import EmailMessage, EmailProvider
from app.shared.logging import logger


class BrevoEmailProvider(EmailProvider):
    name = "brevo"

    def __init__(self, api_key: str):
        configuration = brevo.Configuration()
        configuration.api_key["api-key"] = api_key
        self._api = brevo.TransactionalEmailsApi(brevo.ApiClient(configuration))

    def send(self, message: EmailMessage) -> bool:
        attachments = [
            brevo.SendSmtpEmailAttachment(
                name=att["filename"],
                content=base64.b64encode(att["content"]).decode(),
            )
            for att in message.attachments
        ]
        email = brevo.SendSmtpEmail(
            sender={"name": message.from_name, "email": message.from_email},
            to=[{"email": message.to}],
            subject=message.subject,
            html_content=message.html_body,
            attachment=attachments or None,
            reply_to={"email": message.reply_to} if message.reply_to else None,
        )
        try:
            self._api.send_transac_email(email)
            return True
        except ApiException as e:
            logger.warning("Brevo send failed", extra={"error": str(e), "to": message.to})
            return False
