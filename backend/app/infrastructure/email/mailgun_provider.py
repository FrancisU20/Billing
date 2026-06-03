
import requests

from app.infrastructure.email.provider import EmailMessage, EmailProvider
from app.shared.logging import logger

MAILGUN_API_URL = "https://api.mailgun.net/v3/{domain}/messages"


class MailgunEmailProvider(EmailProvider):
    name = "mailgun"

    def __init__(self, api_key: str, domain: str):
        self._api_key = api_key
        self._domain = domain

    def send(self, message: EmailMessage) -> bool:
        files = [("attachment", (att["filename"], att["content"], att["content_type"]))
                 for att in message.attachments]
        data = {
            "from": f"{message.from_name} <{message.from_email}>",
            "to": message.to,
            "subject": message.subject,
            "html": message.html_body,
        }
        if message.reply_to:
            data["h:Reply-To"] = message.reply_to

        try:
            response = requests.post(
                MAILGUN_API_URL.format(domain=self._domain),
                auth=("api", self._api_key),
                data=data,
                files=files or None,
                timeout=15,
            )
            if response.status_code in (200, 202):
                return True
            logger.warning("Mailgun send failed", extra={"status": response.status_code, "to": message.to})
            return False
        except Exception as e:
            logger.warning("Mailgun exception", extra={"error": str(e)})
            return False
