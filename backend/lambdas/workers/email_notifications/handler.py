"""
Worker: email notifications.

Triggered por: SQS ← OwnerCreatedEvent (emitido por tenant_onboarding worker)

Flujo:
    OwnerCreatedEvent en SQS
        → extrae email, nombre_rep_legal, temp_password
        → SendWelcomeEmailUseCase → envía email de bienvenida via Brevo
        → usuario recibe credenciales de acceso inicial

Eventos reconocidos:
    OwnerCreatedEvent — welcome email al owner de un tenant recién creado

Cualquier evento desconocido se ignora (no suma al batch failure).
"""
from __future__ import annotations

from lambdas._base.sqs_handler import SQSRecord, sqs_handler
from lambdas.workers.email_notifications.infra.brevo_email_sender import BrevoEmailSender
from lambdas.workers.email_notifications.use_cases.send_welcome_email import (
    SendWelcomeEmailUseCase,
)
from shared.logger import get_logger

_log = get_logger(__name__)

# ── Cold start ────────────────────────────────────────────────────────────────
_email_sender = BrevoEmailSender()


@sqs_handler
def handler(record: SQSRecord, context) -> None:
    event_type = record.body.get("event_type")

    if event_type != "OwnerCreatedEvent":
        _log.warning("evento desconocido ignorado", event_type=event_type)
        return

    data = record.body.get("data", {})
    SendWelcomeEmailUseCase(_email_sender).execute(
        email            = data.get("email", ""),
        nombre_rep_legal = data.get("nombre_rep_legal", ""),
        temp_password    = data.get("temp_password", ""),
    )
