from __future__ import annotations
"""Cognito implementation of the IdentityProvider port."""

import boto3

from lambdas.workers.tenant_onboarding.ports import IdentityProvider
from shared.config import env
from shared.logger import get_logger

_log = get_logger(__name__)
_ONBOARDING_STATUSES = {"FORCE_CHANGE_PASSWORD", "RESET_REQUIRED"}


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
            _log.warning("user already exists in Cognito", email=email)
            return False

    def reset_temporary_password(
        self, *, email: str, temporary_password: str
    ) -> bool:
        response = self._idp.admin_get_user(
            UserPoolId = self._user_pool_id,
            Username   = email,
        )
        status = response.get("UserStatus", "")
        if status not in _ONBOARDING_STATUSES:
            _log.info(
                "existing Cognito user already completed onboarding",
                email=email,
                status=status,
            )
            return False

        self._idp.admin_set_user_password(
            UserPoolId = self._user_pool_id,
            Username   = email,
            Password   = temporary_password,
            Permanent  = False,
        )
        _log.info(
            "temporary password reset for existing Cognito user",
            email=email,
            status=status,
        )
        return True
