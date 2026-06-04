from datetime import UTC, datetime

import pytest
from botocore.exceptions import ClientError

from app.infrastructure.security import certificate_service as service
from app.infrastructure.security.certificate_keys import (
    certificate_secret_name,
    certificate_storage_key,
    certificate_upload_key,
)


def test_certificate_key_conventions():
    tenant_id = "tenant-123"
    cert_id = "cert-456"

    assert certificate_upload_key(tenant_id, cert_id) == "tenants/tenant-123/certs/uploads/cert-456.p12"
    assert certificate_storage_key(tenant_id, cert_id) == "tenants/tenant-123/certs/cert-456.p12"
    assert certificate_secret_name(tenant_id, cert_id).endswith("/tenant/tenant-123/cert/cert-456")


def test_validate_and_store_certificate_derives_upload_key_and_uses_kms(monkeypatch):
    fake_s3 = FakeS3()
    fake_secrets = FakeSecrets()

    monkeypatch.setattr(service.settings, "s3_documents_bucket", "documents-bucket")
    monkeypatch.setattr(service.settings, "certificate_secrets_kms_key_arn", "arn:aws:kms:sa-east-1:123:key/certs")
    monkeypatch.setattr(service.boto3, "client", fake_boto3_client(fake_s3, fake_secrets))
    monkeypatch.setattr(
        service.pkcs12,
        "load_key_and_certificates",
        lambda _p12_data, _password: (object(), FakeCertificate(), []),
    )

    metadata = service.validate_and_store_certificate(
        tenant_id="tenant-123",
        cert_id="cert-456",
        password="secret",
    )

    assert fake_s3.read_key == "tenants/tenant-123/certs/uploads/cert-456.p12"
    assert fake_s3.copied_to == "tenants/tenant-123/certs/cert-456.p12"
    assert fake_s3.deleted_key == "tenants/tenant-123/certs/uploads/cert-456.p12"
    assert fake_secrets.created_secret["KmsKeyId"] == "arn:aws:kms:sa-east-1:123:key/certs"
    assert metadata["s3_key"] == "tenants/tenant-123/certs/cert-456.p12"
    assert metadata["fecha_emision"].isoformat() == "2024-01-01"
    assert metadata["fecha_expiracion"].isoformat() == "2026-01-01"


def test_validate_and_store_certificate_reports_missing_temp_upload(monkeypatch):
    fake_s3 = MissingObjectS3()
    fake_secrets = FakeSecrets()

    monkeypatch.setattr(service.settings, "s3_documents_bucket", "documents-bucket")
    monkeypatch.setattr(service.boto3, "client", fake_boto3_client(fake_s3, fake_secrets))

    with pytest.raises(service.CertificateValidationError, match="archivo temporal"):
        service.validate_and_store_certificate(
            tenant_id="tenant-123",
            cert_id="cert-456",
            password="secret",
        )


class FakeBody:
    def read(self):
        return b"p12-data"


class FakeS3:
    read_key: str | None = None
    copied_to: str | None = None
    deleted_key: str | None = None

    def get_object(self, **kwargs):
        self.read_key = kwargs["Key"]
        return {"Body": FakeBody()}

    def copy_object(self, **kwargs):
        self.copied_to = kwargs["Key"]

    def delete_object(self, **kwargs):
        self.deleted_key = kwargs["Key"]


class MissingObjectS3(FakeS3):
    def get_object(self, **kwargs):
        raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")


class ResourceExistsError(Exception):
    pass


class FakeSecretExceptions:
    ResourceExistsException = ResourceExistsError


class FakeSecrets:
    exceptions = FakeSecretExceptions

    def __init__(self):
        self.created_secret = None

    def create_secret(self, **kwargs):
        self.created_secret = kwargs
        return {"ARN": "arn:aws:secretsmanager:sa-east-1:123:secret:cert"}


class FakeSubject:
    def rfc4514_string(self):
        return "CN=Test"


class FakeCertificate:
    not_valid_before_utc = datetime(2024, 1, 1, tzinfo=UTC)
    not_valid_after_utc = datetime(2026, 1, 1, tzinfo=UTC)
    subject = FakeSubject()


def fake_boto3_client(fake_s3, fake_secrets):
    def _client(service_name, *args, **kwargs):
        if service_name == "s3":
            return fake_s3
        if service_name == "secretsmanager":
            return fake_secrets
        raise AssertionError(f"Unexpected boto3 client: {service_name}")

    return _client
