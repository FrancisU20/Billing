from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.certificates.metadata import CertificateMetadata
from shared.certificates.store import CertificateStore
from shared.certificates.validator import CertificateValidator


@dataclass(frozen=True)
class UpdateCertificateResult:
    tenant: Tenant
    metadata: CertificateMetadata
    secret_arn: str
    uploaded_at: datetime


class UpdateCertificateUseCase:
    def __init__(
        self,
        tenant_repo: ITenantRepository,
        certificate_validator: CertificateValidator,
        certificate_store: CertificateStore,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._certificate_validator = certificate_validator
        self._certificate_store = certificate_store

    def execute(
        self,
        *,
        tenant_id: str,
        certificate_b64: str,
        cert_password: str,
        updated_by: str,
    ) -> UpdateCertificateResult:
        tenant = self._tenant_repo.get_by_id(tenant_id)
        metadata = self._certificate_validator.validate_base64(
            certificate_b64=certificate_b64,
            password=cert_password,
            expected_ruc=tenant.ruc,
        )
        secret_arn = self._certificate_store.put_certificate(
            tenant_id=tenant.id,
            certificate_b64=certificate_b64,
            password=cert_password,
        )
        uploaded_at = datetime.now(UTC)
        tenant.attach_certificate(
            metadata,
            secret_arn=secret_arn,
            uploaded_at=uploaded_at,
            updated_by=updated_by,
        )
        return UpdateCertificateResult(
            tenant=tenant,
            metadata=metadata,
            secret_arn=secret_arn,
            uploaded_at=uploaded_at,
        )

    def reattach(
        self,
        *,
        tenant_id: str,
        result: UpdateCertificateResult,
        updated_by: str,
    ) -> Tenant:
        """Re-fetch the tenant at its current version and reapply already-validated
        certificate metadata.

        Used to retry `repo.commit()` after an `OptimisticLockError`: the p12 was
        already validated and the secret already written (idempotent, same secret
        name), so neither needs to be redone — only the tenant projection needs to
        catch up to the latest version before retrying the transactional commit.
        """
        tenant = self._tenant_repo.get_by_id(tenant_id)
        tenant.attach_certificate(
            result.metadata,
            secret_arn=result.secret_arn,
            uploaded_at=result.uploaded_at,
            updated_by=updated_by,
        )
        return tenant
