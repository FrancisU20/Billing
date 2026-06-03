import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.infrastructure.email.provider import EmailMessage, EmailProvider
from app.shared.logging import logger

_SMTP_HOST = "smtp-relay.brevo.com"
_SMTP_PORT = 587


class BrevoEmailProvider(EmailProvider):
    name = "brevo"

    def __init__(self, smtp_user: str, smtp_password: str) -> None:
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password

    def send(self, message: EmailMessage) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = message.subject
        msg["From"] = f"{message.from_name} <{message.from_email}>"
        msg["To"] = message.to

        msg.attach(MIMEText(message.html_body, "html", "utf-8"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(self._smtp_user, self._smtp_password)
                server.sendmail(message.from_email, message.to, msg.as_string())
            return True
        except Exception as e:
            logger.warning("Brevo SMTP send failed", extra={"error": str(e), "to": message.to})
            return False
