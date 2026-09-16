from __future__ import annotations

import boto3

from lambdas.onboarding.domain.repositories.i_identity_provider import IIdentityProvider
from shared.config import env


class CognitoIdentityProvider(IIdentityProvider):
    def __init__(self) -> None:
        self._user_pool_id = env("COGNITO_USER_POOL_ID")
        self._idp = boto3.client("cognito-idp")

    def email_exists(self, email: str) -> bool:
        response = self._idp.list_users(
            UserPoolId=self._user_pool_id,
            Filter=f'username = "{email}"',
            Limit=1,
        )
        return bool(response.get("Users"))
