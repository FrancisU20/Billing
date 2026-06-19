from __future__ import annotations

"""Onboarding Lambda — public OTP based registration flow."""

from lambdas._base.handler import public_lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse
from lambdas._base.response import ApiResponse
from lambdas.onboarding.domain.commands import (
    ConfirmOnboardingOtpCommand,
    RequestOnboardingOtpCommand,
)
from lambdas.onboarding.infra.enterprise_lead_repository import DynamoEnterpriseLeadRepository
from lambdas.onboarding.infra.onboarding_commit_repository import DynamoOnboardingCommitRepository
from lambdas.onboarding.infra.onboarding_verification_repository import (
    DynamoOnboardingVerificationRepository,
)
from lambdas.onboarding.infra.plan_catalog import DynamoPlanCatalog
from lambdas.onboarding.schemas import OnboardingOtpConfirmRequest, OnboardingRequest
from lambdas.onboarding.use_cases.confirm_onboarding_otp import ConfirmOnboardingOtpUseCase
from lambdas.onboarding.use_cases.request_onboarding_otp import RequestOnboardingOtpUseCase
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from shared.certificates.store import CertificateStore
from shared.certificates.validator import CertificateValidator
from shared.config import env
from shared.dates import isoformat_ecuador
from shared.db.client import get_table
from shared.errors import NotFoundError

# ── Cold start ────────────────────────────────────────────────────────────────
_TENANTS_TABLE = get_table("TENANTS_TABLE")
_PLANS_TABLE = get_table("PLANS_TABLE")
_AUDIT_TABLE = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None
_OUTBOX_TABLE = get_table("OUTBOX_TABLE") if env("OUTBOX_TABLE", "") else None


def _tenant_repo() -> DynamoTenantRepository:
    return DynamoTenantRepository(_TENANTS_TABLE, _AUDIT_TABLE, _OUTBOX_TABLE)


def _lead_repo() -> DynamoEnterpriseLeadRepository:
    return DynamoEnterpriseLeadRepository(_TENANTS_TABLE, _OUTBOX_TABLE)


def _verification_repo() -> DynamoOnboardingVerificationRepository:
    return DynamoOnboardingVerificationRepository(_TENANTS_TABLE, _OUTBOX_TABLE)


def _plan_catalog() -> DynamoPlanCatalog:
    return DynamoPlanCatalog(_PLANS_TABLE)


def _commit_repo() -> DynamoOnboardingCommitRepository:
    return DynamoOnboardingCommitRepository(_tenant_repo(), _lead_repo(), _verification_repo())


def _certificate_validator() -> CertificateValidator:
    return CertificateValidator()


def _certificate_store() -> CertificateStore:
    return CertificateStore()


# ── Handlers ──────────────────────────────────────────────────────────────────


@public_lambda_handler
@idempotent
def _request_otp(request: Request, context) -> dict:
    body = parse(OnboardingRequest, request.body)
    command = RequestOnboardingOtpCommand(
        ruc=body.ruc,
        trade_name=body.trade_name,
        legal_name=body.legal_name,
        legal_rep_name=body.legal_rep_name,
        email=body.email,
        phone=body.phone,
        address=body.address,
        accounting_required=body.accounting_required,
        plan_id=body.plan_id,
        certificate_b64=body.certificate_b64,
        cert_password=body.cert_password,
    )
    result = RequestOnboardingOtpUseCase(
        _plan_catalog(),
        _tenant_repo(),
        _certificate_validator(),
    ).execute(command)

    response = ApiResponse.created(
        {
            "verification_id": result.verification.id,
            "expires_at": isoformat_ecuador(result.verification.expires_at),
            "self_service": result.verification.self_service,
        },
        request.request_id,
    )
    _verification_repo().commit_request(
        verification=result.verification,
        events=result.events,
        idempotency=require_current_context(),
        response=response,
    )
    return response


@public_lambda_handler
@idempotent
def _confirm_otp(request: Request, context) -> dict:
    body = parse(OnboardingOtpConfirmRequest, request.body)
    command = ConfirmOnboardingOtpCommand(
        verification_id=body.verification_id,
        otp=body.otp,
        ruc=body.ruc,
        trade_name=body.trade_name,
        legal_name=body.legal_name,
        legal_rep_name=body.legal_rep_name,
        email=body.email,
        phone=body.phone,
        address=body.address,
        accounting_required=body.accounting_required,
        plan_id=body.plan_id,
        certificate_b64=body.certificate_b64,
        cert_password=body.cert_password,
        order_id=body.order_id,
    )
    result = ConfirmOnboardingOtpUseCase(
        _plan_catalog(),
        _tenant_repo(),
        _verification_repo(),
        _certificate_validator(),
        _certificate_store(),
    ).execute(command)

    if result.tenant:
        response = ApiResponse.created(
            {"tenant_id": result.tenant.id, "email": result.tenant.email}, request.request_id
        )
        try:
            _commit_repo().commit_tenant_registration(
                tenant=result.tenant,
                verification=result.verification,
                events=result.events,
                idempotency=require_current_context(),
                response=response,
            )
        except Exception:
            _certificate_store().delete_certificate(tenant_id=result.tenant.id)
            raise
        return response

    response = ApiResponse.created({"message": "Te contactaremos pronto."}, request.request_id)
    _commit_repo().commit_enterprise_lead(
        lead=result.lead,
        verification=result.verification,
        events=result.events,
        idempotency=require_current_context(),
        response=response,
    )
    return response


# ── Entry point AWS ───────────────────────────────────────────────────────────


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path = ctx.get("http", {}).get("path", "")

    if path == "/onboarding/otp/request" and method == "POST":
        return _request_otp(event, context)

    if path == "/onboarding/otp/confirm" and method == "POST":
        return _confirm_otp(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
