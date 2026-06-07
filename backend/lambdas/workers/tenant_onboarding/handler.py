from __future__ import annotations

"""
Worker: tenant onboarding.

Triggered by: SQS ← TenantCreatedEvent (via OutboxRelayWorker)

Flow:
    TenantCreatedEvent in SQS
        → OnboardTenantUseCase → creates owner in Cognito (SUPPRESS native email)
        → if user was created → publishes OwnerCreatedEvent to email_notifications queue
        → email_notifications worker → sends welcome email via Brevo
"""

from lambdas._base.sqs_handler import SQSRecord, sqs_handler
from lambdas.workers.tenant_onboarding.events import OwnerCreatedEvent
from lambdas.workers.tenant_onboarding.infra.cognito_identity_provider import (
    CognitoIdentityProvider,
)
from lambdas.workers.tenant_onboarding.infra.sqs_event_publisher import SQSEventPublisher
from lambdas.workers.tenant_onboarding.use_case import OnboardTenantUseCase
from shared.config import env
from shared.logger import get_logger

_log = get_logger(__name__)

# ── Cold start ────────────────────────────────────────────────────────────────
_identity_provider = CognitoIdentityProvider()
_event_publisher = SQSEventPublisher(queue_url=env("EMAIL_NOTIFICATIONS_QUEUE_URL", ""))


@sqs_handler
def handler(record: SQSRecord, context) -> None:
    event_type = record.body.get("event_type")

    if event_type != "TenantCreatedEvent":
        _log.warning("unknown event ignored", event_type=event_type)
        return

    data = record.body.get("data", {})
    tenant_id = data.get("tenant_id", "")
    email = data.get("email", "")
    legal_rep_name = data.get("legal_rep_name", "")

    temp_password = OnboardTenantUseCase(_identity_provider).execute(
        tenant_id=tenant_id,
        email=email,
        legal_rep_name=legal_rep_name,
    )

    if temp_password:
        _event_publisher.publish(
            OwnerCreatedEvent(
                tenant_id=tenant_id,
                email=email,
                legal_rep_name=legal_rep_name,
                temp_password=temp_password,
            )
        )
