from __future__ import annotations

"""Use case: send the password reset code email."""

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendPasswordResetUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(self, *, email: str, code: str, expires_at: str) -> None:
        if not email or not code:
            raise ValidationError("email and code are required to send password reset")

        try:
            self._email_sender.send_password_reset(
                email=email,
                code=code,
                expires_at=expires_at,
            )
            _log.info("password reset email sent", email=email)
        except Exception as exc:
            _log.error("error sending password reset email", error=str(exc), exc_info=True)
            raise InternalError() from exc
