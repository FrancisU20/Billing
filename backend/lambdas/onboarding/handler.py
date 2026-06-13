from __future__ import annotations

"""
Onboarding Lambda — AWS entry point.

Routes:
    POST /onboarding  registro self-service del tenant (publico, sin JWT)

Si el plan elegido tiene `self_service=true`, crea el Tenant directamente
(arranca en `sri_environment=testing`). Si tiene `self_service=false` (solo
Enterprise), crea un registro ENTERPRISE_LEAD para seguimiento manual del
equipo comercial — ver context/ONBOARDING.md.
"""

from lambdas._base.handler import public_lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse
from lambdas._base.response import ApiResponse
from lambdas.onboarding.domain.commands import RegisterTenantCommand
from lambdas.onboarding.infra.enterprise_lead_repository import DynamoEnterpriseLeadRepository
from lambdas.onboarding.infra.plan_catalog import DynamoPlanCatalog
from lambdas.onboarding.schemas import OnboardingRequest
from lambdas.onboarding.use_cases.register_tenant_use_case import RegisterTenantUseCase
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from shared.config import env
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


def _plan_catalog() -> DynamoPlanCatalog:
    return DynamoPlanCatalog(_PLANS_TABLE)


# ── Handlers ──────────────────────────────────────────────────────────────────


@public_lambda_handler
@idempotent
def _register(request: Request, context) -> dict:
    body = parse(OnboardingRequest, request.body)
    command = RegisterTenantCommand(
        ruc=body.ruc,
        trade_name=body.trade_name,
        legal_name=body.legal_name,
        legal_rep_name=body.legal_rep_name,
        email=body.email,
        phone=body.phone,
        address=body.address,
        accounting_required=body.accounting_required,
        plan_id=body.plan_id,
    )
    result = RegisterTenantUseCase(_plan_catalog(), _tenant_repo()).execute(command)

    if result.tenant:
        response = ApiResponse.created(
            {"tenant_id": result.tenant.id, "email": result.tenant.email}, request.request_id
        )
        _tenant_repo().commit(
            tenant=result.tenant,
            user_id="onboarding",
            action="CREATE",
            events=result.events,
            idempotency=require_current_context(),
            response=response,
        )
        return response

    response = ApiResponse.created({"message": "Te contactaremos pronto."}, request.request_id)
    _lead_repo().commit(
        lead=result.lead,
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

    if path == "/onboarding" and method == "POST":
        return _register(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
