from __future__ import annotations

"""Use case: send the welcome email to the owner of a newly created tenant."""

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendWelcomeEmailUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(self, *, email: str, legal_rep_name: str, temp_password: str) -> None:
        if not email or not temp_password:
            raise ValidationError("email and temp_password are required to send the welcome email")

        try:
            self._email_sender.send_welcome(
                email=email,
                legal_rep_name=legal_rep_name,
                temp_password=temp_password,
            )
            _log.info("welcome email sent", email=email)
        except Exception as exc:
            _log.error("error sending welcome email", error=str(exc), exc_info=True)
            raise InternalError()
