import base64

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

from app.infrastructure.email.provider import EmailMessage, EmailProvider
from app.shared.logging import logger


class BrevoEmailProvider(EmailProvider):
    name = "brevo"

    def __init__(self, api_key: str):
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = api_key
        self._api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    def send(self, message: EmailMessage) -> bool:
        attachments = [
            sib_api_v3_sdk.SendSmtpEmailAttachment(
                name=att["filename"],
                content=base64.b64encode(att["content"]).decode(),
            )
            for att in message.attachments
        ]
        email = sib_api_v3_sdk.SendSmtpEmail(
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
