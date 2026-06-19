from __future__ import annotations

from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from shared.dates import isoformat_ecuador


class GetCertificateUseCase:
    def __init__(self, tenant_repo: ITenantRepository) -> None:
        self._tenant_repo = tenant_repo

    def execute(self, tenant_id: str) -> dict:
        tenant = self._tenant_repo.get_by_id(tenant_id)
        return {
            "tenant_id": tenant.id,
            "cert_subject_ruc": tenant.cert_subject_ruc,
            "cert_expires_at": isoformat_ecuador(tenant.cert_expires_at),
            "cert_issuer": tenant.cert_issuer,
            "cert_uploaded_at": isoformat_ecuador(tenant.cert_uploaded_at),
        }
