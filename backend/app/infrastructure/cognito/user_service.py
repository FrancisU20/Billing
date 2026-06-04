import os
import secrets
import string

import boto3
from aws_lambda_powertools import Logger

from app.shared.config import get_settings

logger = Logger(service="codelabs-billing-cognito")

_SPECIAL = "!@#$%^&*"


def _generate_temp_password() -> str:
    alphabet = string.ascii_letters + string.digits + _SPECIAL
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(14))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in _SPECIAL for c in pwd)
        ):
            return pwd


class CognitoUserService:
    def __init__(self) -> None:
        settings = get_settings()
        self._user_pool_id = settings.cognito_user_pool_id
        region = os.environ.get("AWS_REGION_NAME", "sa-east-1")
        self._client = boto3.client("cognito-idp", region_name=region)

    def create_tenant_admin(self, tenant_id: str, email: str) -> str:
        """Crea el usuario admin del tenant en Cognito. Retorna la contraseña temporal."""
        temp_password = _generate_temp_password()

        self._client.admin_create_user(
            UserPoolId=self._user_pool_id,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "custom:tenant_id", "Value": tenant_id},
                {"Name": "custom:role", "Value": "admin"},
                {"Name": "custom:is_superadmin", "Value": "false"},
            ],
            MessageAction="SUPPRESS",
        )

        self._client.admin_set_user_password(
            UserPoolId=self._user_pool_id,
            Username=email,
            Password=temp_password,
            Permanent=True,
        )

        logger.info("Cognito tenant admin created", extra={"tenant_id": tenant_id})
        return temp_password
