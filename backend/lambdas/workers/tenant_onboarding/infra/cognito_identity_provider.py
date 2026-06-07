"""Cognito implementation of the IdentityProvider port."""
from __future__ import annotations

import boto3

from lambdas.workers.tenant_onboarding.ports import IdentityProvider
from shared.config import env
from shared.logger import get_logger

_log = get_logger(__name__)


class CognitoIdentityProvider(IdentityProvider):
    def __init__(self) -> None:
        self._user_pool_id = env("COGNITO_USER_POOL_ID")
        self._idp = boto3.client("cognito-idp")

    def create_owner(
        self, *, tenant_id: str, email: str, temporary_password: str
    ) -> bool:
        try:
            self._idp.admin_create_user(
                UserPoolId        = self._user_pool_id,
                Username          = email,
                TemporaryPassword = temporary_password,
                MessageAction     = "SUPPRESS",  # Brevo handles the welcome email
                UserAttributes    = [
                    {"Name": "email",                "Value": email},
                    {"Name": "email_verified",       "Value": "true"},
                    {"Name": "custom:tenant_id",     "Value": tenant_id},
                    {"Name": "custom:role",          "Value": "owner"},
                    {"Name": "custom:is_superadmin", "Value": "false"},
                ],
            )
            _log.info("tenant owner created in Cognito", tenant_id=tenant_id, email=email)
            return True

        except self._idp.exceptions.UsernameExistsException:
            _log.warning("user already exists in Cognito — email skipped", email=email)
            return False
