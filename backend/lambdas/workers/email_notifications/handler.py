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

Any unknown event is ignored (does not count as a batch failure).
"""

from lambdas._base.sqs_handler import SQSRecord, sqs_handler
from lambdas.workers.email_notifications.infra.brevo_email_sender import BrevoEmailSender
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
from shared.logger import get_logger

_log = get_logger(__name__)

# ── Cold start ────────────────────────────────────────────────────────────────
_email_sender = BrevoEmailSender()
_SUPERADMIN_EMAIL = env("SUPERADMIN_EMAIL", "")


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

    _log.warning("unknown event ignored", event_type=event_type)
