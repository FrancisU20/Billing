from __future__ import annotations

import json

import boto3
from botocore.exceptions import ClientError

from shared.config import env
from shared.errors import ExternalServiceError
from shared.logger import get_logger

_log = get_logger(__name__)


class CertificateStore:
    def __init__(self, client=None, *, secret_prefix: str | None = None) -> None:
        self._client = client or boto3.client("secretsmanager")
        self._secret_prefix = secret_prefix or env(
            "CERTIFICATE_SECRET_PREFIX",
            f"/codelabs-billing/{env('ENV', 'dev')}/tenant",
        )

    def put_certificate(
        self,
        *,
        tenant_id: str,
        certificate_b64: str,
        password: str,
    ) -> str:
        secret_name = self.secret_name(tenant_id)
        secret_string = json.dumps(
            {"p12_b64": certificate_b64, "password": password},
            separators=(",", ":"),
        )

        try:
            response = self._client.create_secret(
                Name=secret_name,
                SecretString=secret_string,
            )
            return response["ARN"]
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ResourceExistsException":
                _log.error("Secrets Manager create_secret error", tenant_id=tenant_id)
                raise ExternalServiceError("no se pudo guardar el certificado") from exc

        try:
            self._client.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_string,
            )
            response = self._client.describe_secret(SecretId=secret_name)
            return response["ARN"]
        except ClientError as exc:
            _log.error("Secrets Manager put_secret_value error", tenant_id=tenant_id)
            raise ExternalServiceError("no se pudo guardar el certificado") from exc

    def delete_certificate(self, *, tenant_id: str) -> None:
        try:
            self._client.delete_secret(
                SecretId=self.secret_name(tenant_id),
                ForceDeleteWithoutRecovery=True,
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ResourceNotFoundException":
                _log.warning("Secrets Manager cleanup failed", tenant_id=tenant_id)

    def secret_name(self, tenant_id: str) -> str:
        return f"{self._secret_prefix.rstrip('/')}/{tenant_id}/certificate"
