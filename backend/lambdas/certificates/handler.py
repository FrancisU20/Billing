from __future__ import annotations

"""Certificates Lambda — authenticated certificate lifecycle endpoints."""

import re

from lambdas._base.handler import lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.permissions import require_role
from lambdas._base.response import ApiResponse
from lambdas.certificates.schemas import CertificateUpdateRequest
from lambdas.certificates.use_cases.get_certificate import GetCertificateUseCase
from lambdas.certificates.use_cases.update_certificate import UpdateCertificateUseCase
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from shared.certificates.store import CertificateStore
from shared.certificates.validator import CertificateValidator
from shared.config import env
from shared.db.client import get_table
from shared.errors import ForbiddenError, NotFoundError, OptimisticLockError

_TENANTS_TABLE = get_table("TENANTS_TABLE")
_AUDIT_TABLE = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None

# Bounded retries for the rare case where another request updates the same
# tenant between the certificate validation and the transactional commit.
_MAX_COMMIT_ATTEMPTS = 3


def _repo() -> DynamoTenantRepository:
    return DynamoTenantRepository(_TENANTS_TABLE, _AUDIT_TABLE, None)


def _certificate_validator() -> CertificateValidator:
    return CertificateValidator()


def _certificate_store() -> CertificateStore:
    return CertificateStore()


def _authorize_tenant(request: Request, tenant_id: str) -> None:
    if request.is_superadmin:
        return
    if request.tenant_id != tenant_id:
        raise ForbiddenError()


@lambda_handler
@require_role("owner", "admin", "viewer", "superadmin")
def _get(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    _authorize_tenant(request, tenant_id)
    data = GetCertificateUseCase(_repo()).execute(tenant_id)
    return ApiResponse.ok(data, request.request_id)


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _put(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    _authorize_tenant(request, tenant_id)
    body = parse(CertificateUpdateRequest, request.body)
    repo = _repo()
    use_case = UpdateCertificateUseCase(
        repo,
        _certificate_validator(),
        _certificate_store(),
    )
    result = use_case.execute(
        tenant_id=tenant_id,
        certificate_b64=body.certificate_b64,
        cert_password=body.cert_password,
        updated_by=request.user_id,
    )
    tenant = result.tenant
    idempotency = require_current_context()

    for attempt in range(1, _MAX_COMMIT_ATTEMPTS + 1):
        response = ApiResponse.ok(_certificate_response(tenant), request.request_id)
        try:
            repo.commit(
                tenant=tenant,
                user_id=request.user_id,
                action="CERTIFICATE",
                events=[],
                idempotency=idempotency,
                response=response,
            )
            return response
        except OptimisticLockError:
            if attempt == _MAX_COMMIT_ATTEMPTS:
                raise
            tenant = use_case.reattach(
                tenant_id=tenant_id,
                result=result,
                updated_by=request.user_id,
            )


_CERTIFICATE_PATTERN = re.compile(r"^/tenants/[^/]+/certificate$")


def _certificate_response(tenant) -> dict:
    return {
        "cert_subject_ruc": tenant.cert_subject_ruc,
        "cert_expires_at": tenant.cert_expires_at.isoformat()
        if tenant.cert_expires_at
        else None,
        "cert_issuer": tenant.cert_issuer,
        "cert_uploaded_at": tenant.cert_uploaded_at.isoformat()
        if tenant.cert_uploaded_at
        else None,
    }


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path = ctx.get("http", {}).get("path", "")

    if _CERTIFICATE_PATTERN.match(path):
        if method == "GET":
            return _get(event, context)
        if method == "PUT":
            return _put(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
