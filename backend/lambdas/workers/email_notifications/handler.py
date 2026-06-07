"""
Worker: email notifications.

Triggered by: SQS ← OwnerCreatedEvent (emitted by tenant_onboarding worker)

Flow:
    OwnerCreatedEvent in SQS
        → extracts email, legal_rep_name, temp_password
        → SendWelcomeEmailUseCase → sends welcome email via Brevo
        → user receives initial access credentials

Recognized events:
    OwnerCreatedEvent — welcome email to the owner of a newly created tenant

Any unknown event is ignored (does not count as a batch failure).
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
        _log.warning("unknown event ignored", event_type=event_type)
        return

    data = record.body.get("data", {})
    SendWelcomeEmailUseCase(_email_sender).execute(
        email          = data.get("email", ""),
        legal_rep_name = data.get("legal_rep_name", ""),
        temp_password  = data.get("temp_password", ""),
    )
