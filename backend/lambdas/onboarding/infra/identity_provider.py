from __future__ import annotations

import boto3

from lambdas.onboarding.domain.repositories.i_identity_provider import IIdentityProvider
from shared.config import env


class CognitoIdentityProvider(IIdentityProvider):
    def __init__(self) -> None:
        self._user_pool_id = env("COGNITO_USER_POOL_ID")
        self._idp = boto3.client("cognito-idp")

    def email_exists(self, email: str) -> bool:
        try:
            self._idp.admin_get_user(UserPoolId=self._user_pool_id, Username=email)
            return True
        except self._idp.exceptions.UserNotFoundException:
            return False
