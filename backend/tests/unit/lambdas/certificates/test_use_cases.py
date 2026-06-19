from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from typing import Any

from lambdas.certificates.use_cases.get_certificate import GetCertificateUseCase
from lambdas.certificates.use_cases.update_certificate import UpdateCertificateUseCase
from shared.certificates.errors import CertificateRucMismatchError
from shared.certificates.metadata import CertificateMetadata
from shared.dates import isoformat_ecuador
from tests.unit.support import VALID_RUC, FakeTenantRepository, make_tenant

SECRET_ARN = "arn:aws:secretsmanager:sa-east-1:123:secret:/tenant/certificate"


class FakeCertificateValidator:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def validate_base64(self, **kwargs: Any) -> CertificateMetadata:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return CertificateMetadata(
            subject_ruc=kwargs["expected_ruc"],
            expires_at=datetime.now(UTC) + timedelta(days=365),
            issuer="Security Data",
        )


class FakeCertificateStore:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, Any]] = []

    def put_certificate(self, **kwargs: Any) -> str:
        self.put_calls.append(kwargs)
        return SECRET_ARN


class GetCertificateUseCaseTests(unittest.TestCase):
    def test_returns_none_metadata_when_certificate_not_uploaded(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1")
        repo.tenants[tenant.id] = tenant

        data = GetCertificateUseCase(repo).execute(tenant.id)

        self.assertEqual(
            data,
            {
                "tenant_id": "tenant-1",
                "cert_subject_ruc": None,
                "cert_expires_at": None,
                "cert_issuer": None,
                "cert_uploaded_at": None,
            },
        )

    def test_returns_certificate_metadata(self) -> None:
        repo = FakeTenantRepository()
        expires_at = datetime.now(UTC) + timedelta(days=100)
        uploaded_at = datetime.now(UTC)
        tenant = make_tenant(
            id="tenant-1",
            cert_subject_ruc=VALID_RUC,
            cert_expires_at=expires_at,
            cert_issuer="Security Data",
            cert_uploaded_at=uploaded_at,
        )
        repo.tenants[tenant.id] = tenant

        data = GetCertificateUseCase(repo).execute(tenant.id)

        self.assertEqual(data["cert_subject_ruc"], VALID_RUC)
        self.assertEqual(data["cert_expires_at"], isoformat_ecuador(expires_at))
        self.assertEqual(data["cert_issuer"], "Security Data")
        self.assertEqual(data["cert_uploaded_at"], isoformat_ecuador(uploaded_at))

    def test_does_not_expose_secret_arn(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1", certificate_secret_arn=SECRET_ARN)
        repo.tenants[tenant.id] = tenant

        data = GetCertificateUseCase(repo).execute(tenant.id)

        self.assertNotIn("certificate_secret_arn", data)


class UpdateCertificateUseCaseTests(unittest.TestCase):
    def test_validates_against_tenant_ruc_stores_secret_and_attaches_metadata(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1", ruc=VALID_RUC)
        repo.tenants[tenant.id] = tenant
        validator = FakeCertificateValidator()
        store = FakeCertificateStore()

        result = UpdateCertificateUseCase(repo, validator, store).execute(
            tenant_id=tenant.id,
            certificate_b64="base64-p12",
            cert_password="secret",
            updated_by="user-1",
        )

        self.assertEqual(validator.calls[0]["expected_ruc"], VALID_RUC)
        self.assertEqual(store.put_calls[0]["tenant_id"], tenant.id)
        self.assertEqual(result.tenant.cert_subject_ruc, VALID_RUC)
        self.assertEqual(result.tenant.certificate_secret_arn, SECRET_ARN)
        self.assertEqual(result.secret_arn, SECRET_ARN)

    def test_propagates_certificate_validation_errors_without_touching_store(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1", ruc=VALID_RUC)
        repo.tenants[tenant.id] = tenant
        validator = FakeCertificateValidator(error=CertificateRucMismatchError())
        store = FakeCertificateStore()

        with self.assertRaises(CertificateRucMismatchError):
            UpdateCertificateUseCase(repo, validator, store).execute(
                tenant_id=tenant.id,
                certificate_b64="base64-p12",
                cert_password="secret",
                updated_by="user-1",
            )

        self.assertEqual(store.put_calls, [])

    def test_reattach_refetches_tenant_and_reapplies_metadata_without_revalidating(self) -> None:
        repo = FakeTenantRepository()
        tenant = make_tenant(id="tenant-1", ruc=VALID_RUC)
        repo.tenants[tenant.id] = tenant
        validator = FakeCertificateValidator()
        store = FakeCertificateStore()
        use_case = UpdateCertificateUseCase(repo, validator, store)

        result = use_case.execute(
            tenant_id=tenant.id,
            certificate_b64="base64-p12",
            cert_password="secret",
            updated_by="user-1",
        )

        # Simulate a concurrent update bumping the tenant's version in storage.
        stored = repo.tenants[tenant.id]
        stored.version += 1
        version_before_reattach = stored.version

        reattached = use_case.reattach(
            tenant_id=tenant.id,
            result=result,
            updated_by="user-1",
        )

        self.assertEqual(reattached.cert_subject_ruc, VALID_RUC)
        self.assertEqual(reattached.certificate_secret_arn, SECRET_ARN)
        self.assertEqual(reattached.version, version_before_reattach + 1)
        # Re-validation and re-upload must not happen on reattach.
        self.assertEqual(len(validator.calls), 1)
        self.assertEqual(len(store.put_calls), 1)


if __name__ == "__main__":
    unittest.main()
