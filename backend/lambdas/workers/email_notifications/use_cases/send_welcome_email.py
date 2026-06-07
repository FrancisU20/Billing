"""Caso de uso: enviar email de bienvenida al owner de un tenant recién creado."""
from __future__ import annotations

from lambdas.workers.email_notifications.ports import EmailSender
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class SendWelcomeEmailUseCase:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender

    def execute(
        self, *, email: str, nombre_rep_legal: str, temp_password: str
    ) -> None:
        if not email or not temp_password:
            raise ValidationError(
                "email y temp_password son requeridos para enviar el welcome email"
            )

        try:
            self._email_sender.send_welcome(
                email=email,
                nombre_rep_legal=nombre_rep_legal,
                temp_password=temp_password,
            )
            _log.info("welcome email enviado", email=email)
        except Exception as exc:
            _log.error("error enviando welcome email", error=str(exc), exc_info=True)
            raise InternalError()
