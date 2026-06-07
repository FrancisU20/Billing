"""
OnboardTenantUseCase — creates the owner user in Cognito.

Receives the TenantCreatedEvent payload and:
1. Generates a temporary password
2. Creates the user in Cognito with role 'owner' and the correct tenant_id
3. Returns the temporary password so the handler can publish OwnerCreatedEvent
   → email_notifications worker uses it to send the welcome email via Brevo

If the user already exists it returns None — the email is not re-sent.
"""
from __future__ import annotations

import secrets
import string

from lambdas.workers.tenant_onboarding.ports import IdentityProvider
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)

_PASSWORD_CHARS = string.ascii_letters + string.digits + "!@#$%^&*"


def _generate_temp_password(length: int = 16) -> str:
    while True:
        pwd = "".join(secrets.choice(_PASSWORD_CHARS) for _ in range(length))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)
        ):
            return pwd


class OnboardTenantUseCase:
    def __init__(self, identity_provider: IdentityProvider) -> None:
        self._identity_provider = identity_provider

    def execute(
        self, tenant_id: str, email: str, legal_rep_name: str
    ) -> str | None:
        """
        Returns temp_password if the owner was created, None if it already existed.
        The password is never logged — it stays in memory until published to SQS (SSE).
        """
        if not tenant_id or not email:
            raise ValidationError("tenant_id and email are required for onboarding")

        temp_password = _generate_temp_password()

        try:
            created = self._identity_provider.create_owner(
                tenant_id=tenant_id,
                email=email,
                temporary_password=temp_password,
            )
        except Exception as e:
            _log.error("error creating user in Cognito", error=str(e), exc_info=True)
            raise InternalError()

        if not created:
            return None

        _log.info("tenant onboarding completed", tenant_id=tenant_id, email=email)
        return temp_password
