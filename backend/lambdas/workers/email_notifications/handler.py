from __future__ import annotations

"""
Worker: email notifications.

Triggered by: SQS ← OwnerCreatedEvent (emitted by tenant_onboarding worker)

Flow:
    OwnerCreatedEvent in SQS
        → extracts email, legal_rep_name, temp_password
        → SendWelcomeEmailUseCase → sends welcome email via Brevo
        → user receives initial access credentials

Recognized events:
    OnboardingOtpRequestedEvent          — verification email for public registration
    OwnerCreatedEvent                    — welcome email to the owner of a newly created tenant
    EnterpriseLeadCreatedEvent           — internal notification to the sales team
    SubscriptionRenewalReminderEvent     — subscription expiry reminder to tenant owner
    SubscriptionExpiredEvent             — subscription expired / account suspended notice
    DocumentAuthorizedEvent              — invoice authorized by the SRI
    DocumentBuyerNotificationRequestedEvent — authorized XML + RIDE delivery to buyer
    DocumentRejectedEvent                — invoice rejected by the SRI
    DocumentFailedPermanentEvent         — SRI authorization could not be confirmed after retries

Any unknown event is ignored (does not count as a batch failure).
"""

from lambdas._base.sqs_handler import SQSRecord, sqs_handler
from lambdas.documents.infra.documents_repository import DynamoDocumentsRepository
from lambdas.workers.email_notifications.infra.brevo_email_sender import BrevoEmailSender
from lambdas.workers.email_notifications.infra.s3_document_attachment_reader import (
    S3DocumentAttachmentReader,
)
from lambdas.workers.email_notifications.use_cases.send_document_authorized import (
    SendDocumentAuthorizedUseCase,
)
from lambdas.workers.email_notifications.use_cases.send_document_failed_permanent import (
    SendDocumentFailedPermanentUseCase,
)
from lambdas.workers.email_notifications.use_cases.send_document_rejected import (
    SendDocumentRejectedUseCase,
)
from lambdas.workers.email_notifications.use_cases.send_document_to_buyer import (
    SendDocumentToBuyerUseCase,
)
from lambdas.workers.email_notifications.use_cases.send_enterprise_lead_notification import (
    SendEnterpriseLeadNotificationUseCase,
)
from lambdas.workers.email_notifications.use_cases.send_onboarding_otp import (
    SendOnboardingOtpUseCase,
)
from lambdas.workers.email_notifications.use_cases.send_subscription_expired import (
    SendSubscriptionExpiredUseCase,
)
from lambdas.workers.email_notifications.use_cases.send_subscription_renewal_reminder import (
    SendSubscriptionRenewalReminderUseCase,
)
from lambdas.workers.email_notifications.use_cases.send_welcome_email import (
    SendWelcomeEmailUseCase,
)
from shared.config import env
from shared.db.client import get_table
from shared.logger import get_logger

_log = get_logger(__name__)

# ── Cold start ────────────────────────────────────────────────────────────────
_email_sender = BrevoEmailSender()
_SUPERADMIN_EMAIL = env("SUPERADMIN_EMAIL", "")
_DOCUMENTS_BUCKET = env("DOCUMENTS_BUCKET", "")
_documents_repo: DynamoDocumentsRepository | None = None
_attachment_reader: S3DocumentAttachmentReader | None = None


def _get_documents_repo() -> DynamoDocumentsRepository:
    global _documents_repo
    if _documents_repo is None:
        _documents_repo = DynamoDocumentsRepository(get_table("DOCUMENTS_TABLE"))
    return _documents_repo


def _get_attachment_reader() -> S3DocumentAttachmentReader:
    global _attachment_reader
    if _attachment_reader is None:
        if not _DOCUMENTS_BUCKET:
            raise RuntimeError("DOCUMENTS_BUCKET is required for buyer document notifications")
        _attachment_reader = S3DocumentAttachmentReader(_DOCUMENTS_BUCKET)
    return _attachment_reader


@sqs_handler
def handler(record: SQSRecord, context) -> None:
    event_type = record.body.get("event_type")
    data = record.body.get("data", {})

    if event_type == "OnboardingOtpRequestedEvent":
        SendOnboardingOtpUseCase(_email_sender).execute(
            email=data.get("email", ""),
            legal_rep_name=data.get("legal_rep_name", ""),
            otp=data.get("otp", ""),
            expires_at=data.get("expires_at", ""),
        )
        return

    if event_type == "OwnerCreatedEvent":
        SendWelcomeEmailUseCase(_email_sender).execute(
            email=data.get("email", ""),
            legal_rep_name=data.get("legal_rep_name", ""),
            temp_password=data.get("temp_password", ""),
        )
        return

    if event_type == "EnterpriseLeadCreatedEvent":
        SendEnterpriseLeadNotificationUseCase(_email_sender).execute(
            superadmin_email=_SUPERADMIN_EMAIL,
            trade_name=data.get("trade_name", ""),
            ruc=data.get("ruc", ""),
            email=data.get("email", ""),
            plan_id=data.get("plan_id", ""),
        )
        return

    if event_type == "SubscriptionRenewalReminderEvent":
        SendSubscriptionRenewalReminderUseCase(_email_sender).execute(
            email=data.get("email", ""),
            legal_rep_name=data.get("legal_rep_name", ""),
            trade_name=data.get("trade_name", ""),
            plan_cycle_ends_at=data.get("plan_cycle_ends_at", ""),
            days_remaining=int(data.get("days_remaining", 0)),
        )
        return

    if event_type == "SubscriptionExpiredEvent":
        SendSubscriptionExpiredUseCase(_email_sender).execute(
            email=data.get("email", ""),
            legal_rep_name=data.get("legal_rep_name", ""),
            trade_name=data.get("trade_name", ""),
        )
        return

    if event_type == "DocumentAuthorizedEvent":
        SendDocumentAuthorizedUseCase(_email_sender).execute(
            email=data.get("tenant_email", ""),
            legal_rep_name=data.get("legal_rep_name", ""),
            document_id=data.get("document_id", ""),
            access_key=data.get("access_key", ""),
            authorization_number=data.get("authorization_number", ""),
        )
        return

    if event_type == "DocumentBuyerNotificationRequestedEvent":
        SendDocumentToBuyerUseCase(
            _get_documents_repo(),
            _get_attachment_reader(),
            _email_sender,
        ).execute(
            tenant_id=data.get("tenant_id", ""),
            document_id=data.get("document_id", ""),
        )
        return

    if event_type == "DocumentRejectedEvent":
        SendDocumentRejectedUseCase(_email_sender).execute(
            email=data.get("tenant_email", ""),
            legal_rep_name=data.get("legal_rep_name", ""),
            document_id=data.get("document_id", ""),
            access_key=data.get("access_key", ""),
            sri_errors=data.get("sri_errors") or [],
        )
        return

    if event_type == "DocumentFailedPermanentEvent":
        SendDocumentFailedPermanentUseCase(_email_sender).execute(
            email=data.get("tenant_email", ""),
            legal_rep_name=data.get("legal_rep_name", ""),
            document_id=data.get("document_id", ""),
            access_key=data.get("access_key", ""),
        )
        return

    _log.warning("unknown event ignored", event_type=event_type)
