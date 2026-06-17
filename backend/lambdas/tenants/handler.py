from __future__ import annotations

"""
Tenants Lambda — AWS entry point.

Routes:
    POST   /tenants                                create tenant    (superadmin)
    GET    /tenants                                list all         (superadmin)
    GET    /tenants/{id}                           get by ID        (superadmin | tenant members)
    PATCH  /tenants/{id}                           update           (superadmin | owner | admin)
    PATCH  /tenants/{id}/status                    change status    (superadmin)
    POST   /tenants/{id}/onboarding/retry          retry onboarding (superadmin)
    DELETE /tenants/{id}                           soft delete      (superadmin)
    POST   /tenants/{id}/subscription/activate     first activation (owner | admin | superadmin)
    POST   /tenants/{id}/subscription/renew        manual renewal   (owner | admin | superadmin)
    POST   /tenants/{id}/subscription/retry-payment retry saved card (owner | admin | superadmin)
"""
import re

from lambdas._base.handler import lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.permissions import require_role, require_superadmin
from lambdas._base.response import ApiResponse
from lambdas.subscriptions.infra.dlocal_client import DLocalClient
from lambdas.subscriptions.infra.payment_repository import DynamoPaymentRepository
from lambdas.tenants.domain.commands import (
    CreateTenantCommand,
    RetryTenantOnboardingCommand,
    ToggleStatusCommand,
    UpdateTenantCommand,
)
from lambdas.tenants.domain.enums import PlanStatus, SriEnvironment, TenantStatus
from lambdas.tenants.infra.payment_reader import DynamoPaymentReader
from lambdas.tenants.infra.plan_catalog import DynamoPlanCatalog
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from lambdas.tenants.schemas import (
    ApplyRenewalRequest,
    CreateTenantRequest,
    ToggleStatusRequest,
    UpdateTenantRequest,
)
from lambdas.tenants.use_cases.activate_subscription import ActivateSubscriptionUseCase
from lambdas.tenants.use_cases.apply_subscription_renewal import ApplySubscriptionRenewalUseCase
from lambdas.tenants.use_cases.create_tenant import CreateTenantUseCase
from lambdas.tenants.use_cases.delete_tenant import DeleteTenantUseCase
from lambdas.tenants.use_cases.get_tenant import GetTenantUseCase
from lambdas.tenants.use_cases.list_tenants import ListTenantsQuery, ListTenantsUseCase
from lambdas.tenants.use_cases.retry_onboarding import RetryTenantOnboardingUseCase
from lambdas.tenants.use_cases.retry_payment import RetryPaymentUseCase
from lambdas.tenants.use_cases.toggle_status import ToggleStatusUseCase
from lambdas.tenants.use_cases.update_tenant import UpdateTenantUseCase
from shared.config import env
from shared.dates import parse_date_boundary
from shared.db.client import get_table
from shared.db.limits import DEFAULT_LIST_LIMIT, clamp_list_limit
from shared.errors import ForbiddenError, NotFoundError, ValidationError
from shared.secrets.client import get_secret_json

# ── Cold start ────────────────────────────────────────────────────────────────
_TABLE = get_table("TENANTS_TABLE")
_PLANS_TABLE = get_table("PLANS_TABLE")
_PAYMENTS_TABLE = get_table("PAYMENTS_TABLE") if env("PAYMENTS_TABLE", "") else None
_AUDIT_TABLE = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None
_OUTBOX_TABLE = get_table("OUTBOX_TABLE") if env("OUTBOX_TABLE", "") else None


def _repo() -> DynamoTenantRepository:
    return DynamoTenantRepository(_TABLE, _AUDIT_TABLE, _OUTBOX_TABLE)


def _plan_catalog() -> DynamoPlanCatalog:
    return DynamoPlanCatalog(_PLANS_TABLE)


def _payment_reader() -> DynamoPaymentReader | None:
    return DynamoPaymentReader(_PAYMENTS_TABLE) if _PAYMENTS_TABLE else None


def _payment_repo() -> DynamoPaymentRepository | None:
    return DynamoPaymentRepository(_PAYMENTS_TABLE) if _PAYMENTS_TABLE else None


def _dlocal_client() -> DLocalClient | None:
    creds_name = env("DLOCALGO_CREDENTIALS_NAME", "")
    if not creds_name:
        return None
    creds = get_secret_json(creds_name)
    return DLocalClient(
        base_url=env("DLOCALGO_API_URL"),
        api_key=creds["api_key"],
        secret_key=creds["secret_key"],
    )


def _parse_list_query(params: dict) -> ListTenantsQuery:
    try:
        limit = int(params.get("limit", DEFAULT_LIST_LIMIT))
    except (TypeError, ValueError) as exc:
        raise ValidationError("limit debe ser un número entero") from exc
    if limit < 1:
        raise ValidationError("limit debe ser mayor a cero")

    status = params.get("status")
    if status:
        try:
            TenantStatus(status)
        except ValueError as exc:
            raise ValidationError(f"Estado inválido: {status}") from exc

    sri_environment = params.get("sri_environment")
    if sri_environment:
        try:
            SriEnvironment(sri_environment)
        except ValueError as exc:
            raise ValidationError("Entorno SRI inválido") from exc

    plan_status = params.get("plan_status")
    if plan_status:
        try:
            PlanStatus(plan_status)
        except ValueError as exc:
            raise ValidationError("Estado de plan inválido") from exc

    return ListTenantsQuery(
        limit=clamp_list_limit(limit),
        next_token=params.get("next_token"),
        status=status,
        q=params.get("q"),
        ruc=params.get("ruc"),
        sri_environment=sri_environment,
        plan_status=plan_status,
        created_from=parse_date_boundary(params.get("created_from"), end_of_day=False),
        created_to=parse_date_boundary(params.get("created_to"), end_of_day=True),
    )


# ── Handlers ──────────────────────────────────────────────────────────────────


@lambda_handler
@require_superadmin
@idempotent
def _create(request: Request, context) -> dict:
    body = parse(CreateTenantRequest, request.body)
    command = CreateTenantCommand(
        ruc=body.ruc,
        trade_name=body.trade_name,
        legal_name=body.legal_name,
        legal_rep_name=body.legal_rep_name,
        email=body.email,
        phone=body.phone,
        address=body.address,
        accounting_required=body.accounting_required,
        plan_id=body.plan_id,
        created_by=request.user_id,
    )
    repo = _repo()
    tenant, events = CreateTenantUseCase(repo, _plan_catalog()).execute(command)
    response = ApiResponse.created(tenant.to_dict(), request.request_id)
    repo.commit(
        tenant=tenant,
        user_id=request.user_id,
        action="CREATE",
        events=events,
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_superadmin
def _list(request: Request, context) -> dict:
    query = _parse_list_query(request.query_params)
    tenants, next_token = ListTenantsUseCase(_repo()).execute(query)
    return ApiResponse.paginated(
        items=[t.to_dict() for t in tenants],
        next_token=next_token,
        request_id=request.request_id,
    )


@lambda_handler
def _get(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    if not request.is_superadmin and request.tenant_id != tenant_id:
        raise ForbiddenError()
    tenant = GetTenantUseCase(_repo()).execute(tenant_id)
    return ApiResponse.ok(tenant.to_dict(), request.request_id)


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _update(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    if not request.is_superadmin and request.tenant_id != tenant_id:
        raise ForbiddenError()

    body = parse(UpdateTenantRequest, request.body)
    command = UpdateTenantCommand(
        tenant_id=tenant_id,
        updated_by=request.user_id,
        trade_name=body.trade_name,
        legal_name=body.legal_name,
        legal_rep_name=body.legal_rep_name,
        email=body.email,
        phone=body.phone,
        address=body.address,
        accounting_required=body.accounting_required,
        sri_environment=body.sri_environment,
    )
    repo = _repo()
    tenant, events = UpdateTenantUseCase(repo).execute(command)
    response = ApiResponse.ok(tenant.to_dict(), request.request_id)
    repo.commit(
        tenant=tenant,
        user_id=request.user_id,
        action="UPDATE",
        events=events,
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_superadmin
@idempotent
def _toggle_status(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    body = parse(ToggleStatusRequest, request.body)
    command = ToggleStatusCommand(
        tenant_id=tenant_id,
        new_status=body.status,
        updated_by=request.user_id,
    )
    repo = _repo()
    tenant, events = ToggleStatusUseCase(repo).execute(command)
    response = ApiResponse.ok(tenant.to_dict(), request.request_id)
    repo.commit(
        tenant=tenant,
        user_id=request.user_id,
        action="STATUS",
        events=events,
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_superadmin
@idempotent
def _retry_onboarding(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    command = RetryTenantOnboardingCommand(
        tenant_id=tenant_id,
        requested_by=request.user_id,
    )
    repo = _repo()
    tenant, events = RetryTenantOnboardingUseCase(repo).execute(command)
    response = ApiResponse.ok(
        {
            "tenant_id": tenant.id,
            "email": tenant.email,
            "status": "queued",
        },
        request.request_id,
    )
    repo.commit_admin_events(
        tenant=tenant,
        user_id=request.user_id,
        action="ONBOARDING_RETRY",
        events=events,
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _activate_subscription(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    if not request.is_superadmin and request.tenant_id != tenant_id:
        raise ForbiddenError()
    body = parse(ApplyRenewalRequest, request.body)
    repo = _repo()
    tenant, result, payment_transact = ActivateSubscriptionUseCase(repo, _payment_reader()).execute(
        tenant_id, body.order_id, request.user_id
    )
    response = ApiResponse.ok(
        {
            "tenant_id": result.tenant_id,
            "plan_cycle_ends_at": result.plan_cycle_ends_at,
            "subscription_status": result.subscription_status,
        },
        request.request_id,
    )
    repo.commit(
        tenant=tenant,
        user_id=request.user_id,
        action="SUBSCRIPTION_ACTIVATION",
        events=[],
        idempotency=require_current_context(),
        response=response,
        extra_transact_items=[payment_transact],
    )
    return response


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _apply_renewal(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    if not request.is_superadmin and request.tenant_id != tenant_id:
        raise ForbiddenError()
    body = parse(ApplyRenewalRequest, request.body)
    repo = _repo()
    tenant, result, payment_transact = ApplySubscriptionRenewalUseCase(
        repo, _payment_reader()
    ).execute(tenant_id, body.order_id, request.user_id)
    response = ApiResponse.ok(
        {
            "tenant_id": result.tenant_id,
            "plan_cycle_ends_at": result.plan_cycle_ends_at,
            "subscription_status": result.subscription_status,
        },
        request.request_id,
    )
    repo.commit(
        tenant=tenant,
        user_id=request.user_id,
        action="SUBSCRIPTION_RENEWAL",
        events=[],
        idempotency=require_current_context(),
        response=response,
        extra_transact_items=[payment_transact],
    )
    return response


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _retry_payment(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    if not request.is_superadmin and request.tenant_id != tenant_id:
        raise ForbiddenError()
    dlocal = _dlocal_client()
    payment_repo = _payment_repo()
    if not dlocal or not payment_repo:
        raise ValidationError("Cobro automático no disponible en este entorno.")
    repo = _repo()
    tenant, result, payment_transact = RetryPaymentUseCase(
        repo, _plan_catalog(), dlocal, payment_repo
    ).execute(tenant_id, request.user_id)
    response = ApiResponse.ok(
        {
            "tenant_id": result.tenant_id,
            "plan_cycle_ends_at": result.plan_cycle_ends_at,
            "subscription_status": result.subscription_status,
        },
        request.request_id,
    )
    repo.commit(
        tenant=tenant,
        user_id=request.user_id,
        action="SUBSCRIPTION_RETRY_PAYMENT",
        events=[],
        idempotency=require_current_context(),
        response=response,
        extra_transact_items=[payment_transact],
    )
    return response


@lambda_handler
@require_superadmin
@idempotent
def _delete(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    repo = _repo()
    tenant, events = DeleteTenantUseCase(repo).execute(tenant_id, request.user_id)
    response = ApiResponse.no_content(request.request_id)
    repo.commit(
        tenant=tenant,
        user_id=request.user_id,
        action="DELETE",
        events=events,
        idempotency=require_current_context(),
        response=response,
    )
    return response


# ── Entry point AWS ───────────────────────────────────────────────────────────

_ID_PATTERN = re.compile(r"^/tenants/[^/]+$")
_STATUS_PATTERN = re.compile(r"^/tenants/[^/]+/status$")
_ONBOARDING_RETRY_PATTERN = re.compile(r"^/tenants/[^/]+/onboarding/retry$")
_SUBSCRIPTION_RENEW_PATTERN = re.compile(r"^/tenants/[^/]+/subscription/renew$")
_SUBSCRIPTION_ACTIVATE_PATTERN = re.compile(r"^/tenants/[^/]+/subscription/activate$")
_SUBSCRIPTION_RETRY_PAYMENT_PATTERN = re.compile(r"^/tenants/[^/]+/subscription/retry-payment$")


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path = ctx.get("http", {}).get("path", "")

    if path == "/tenants":
        if method == "POST":
            return _create(event, context)
        if method == "GET":
            return _list(event, context)

    if _STATUS_PATTERN.match(path):
        if method == "PATCH":
            return _toggle_status(event, context)

    if _ONBOARDING_RETRY_PATTERN.match(path):
        if method == "POST":
            return _retry_onboarding(event, context)

    if _SUBSCRIPTION_ACTIVATE_PATTERN.match(path):
        if method == "POST":
            return _activate_subscription(event, context)

    if _SUBSCRIPTION_RENEW_PATTERN.match(path):
        if method == "POST":
            return _apply_renewal(event, context)

    if _SUBSCRIPTION_RETRY_PAYMENT_PATTERN.match(path):
        if method == "POST":
            return _retry_payment(event, context)

    if _ID_PATTERN.match(path):
        if method == "GET":
            return _get(event, context)
        if method == "PATCH":
            return _update(event, context)
        if method == "DELETE":
            return _delete(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
