from __future__ import annotations

from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository


class GetCertificateUseCase:
    def __init__(self, tenant_repo: ITenantRepository) -> None:
        self._tenant_repo = tenant_repo

    def execute(self, tenant_id: str) -> dict:
        tenant = self._tenant_repo.get_by_id(tenant_id)
        return {
            "tenant_id": tenant.id,
            "cert_subject_ruc": tenant.cert_subject_ruc,
            "cert_expires_at": tenant.cert_expires_at.isoformat()
            if tenant.cert_expires_at
            else None,
            "cert_issuer": tenant.cert_issuer,
            "cert_uploaded_at": tenant.cert_uploaded_at.isoformat()
            if tenant.cert_uploaded_at
            else None,
        }
