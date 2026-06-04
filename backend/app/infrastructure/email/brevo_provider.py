import requests

from app.infrastructure.email.provider import EmailMessage, EmailProvider
from app.shared.logging import logger

_BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoEmailProvider(EmailProvider):
    name = "brevo"

    def __init__(self, api_key: str) -> None:
        self._headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def send(self, message: EmailMessage) -> bool:
        payload = {
            "sender": {"name": message.from_name, "email": message.from_email},
            "to": [{"email": message.to}],
            "subject": message.subject,
            "htmlContent": message.html_body,
        }
        if message.reply_to:
            payload["replyTo"] = {"email": message.reply_to}

        try:
            response = requests.post(
                _BREVO_SEND_URL,
                json=payload,
                headers=self._headers,
                timeout=15,
            )
            response.raise_for_status()
            return True
        except requests.HTTPError as e:
            logger.warning("Brevo API error", extra={
                "status": e.response.status_code, "body": e.response.text[:200], "to": message.to,
            })
            return False
        except Exception as e:
            logger.warning("Brevo send failed", extra={"error": str(e), "to": message.to})
            return False
