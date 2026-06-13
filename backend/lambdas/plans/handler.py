from __future__ import annotations

"""
Plans Lambda — AWS entry point.

Routes:
    POST   /plans              create plan            (superadmin)
    GET    /plans              list plans             (public — no auth)
    GET    /plans/{slug}       get by slug            (public — no auth)
    PATCH  /plans/{id}         update by UUID         (superadmin)
    PATCH  /plans/{id}/status  activate/deactivate    (superadmin)

GET is public so the frontend can render the pricing table without login.
Public routes always return only active plans — inactive plans are hidden from the catalog.
Mutations use the UUID (id) — stable even if the slug changes.
"""
import re

from lambdas._base.handler import lambda_handler, public_lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.permissions import require_superadmin
from lambdas._base.response import ApiResponse
from lambdas.plans.domain.commands import (
    CreatePlanCommand,
    TogglePlanCommand,
    UpdatePlanCommand,
)
from lambdas.plans.domain.errors import PlanNotFoundError
from lambdas.plans.infra.plan_repository import DynamoPlanRepository
from lambdas.plans.schemas import CreatePlanRequest, TogglePlanRequest, UpdatePlanRequest
from lambdas.plans.use_cases.create_plan import CreatePlanUseCase
from lambdas.plans.use_cases.get_plan import GetPlanBySlugUseCase
from lambdas.plans.use_cases.list_plans import ListPlansQuery, ListPlansUseCase
from lambdas.plans.use_cases.toggle_plan import TogglePlanUseCase
from lambdas.plans.use_cases.update_plan import UpdatePlanUseCase
from shared.config import env
from shared.dates import parse_date_boundary
from shared.db.client import get_table
from shared.errors import NotFoundError, ValidationError

_table = get_table("PLANS_TABLE")
_audit_table = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None


def _repo() -> DynamoPlanRepository:
    return DynamoPlanRepository(_table, _audit_table)


def _parse_list_query(params: dict) -> ListPlansQuery:
    status = params.get("status")
    if status and status not in ("active", "inactive"):
        raise ValidationError("Estado inválido")

    limit_cycle = params.get("limit_cycle")
    if limit_cycle and limit_cycle not in ("month", "year"):
        raise ValidationError("Ciclo de límite inválido")

    return ListPlansQuery(
        status=status,
        slug=params.get("slug"),
        q=params.get("q"),
        limit_cycle=limit_cycle,
        created_from=parse_date_boundary(params.get("created_from"), end_of_day=False),
        created_to=parse_date_boundary(params.get("created_to"), end_of_day=True),
    )


# ── Handlers ──────────────────────────────────────────────────────────────────


@lambda_handler
@require_superadmin
@idempotent
def _create(request: Request, context) -> dict:
    body = parse(CreatePlanRequest, request.body)
    repo = _repo()
    plan = CreatePlanUseCase(repo).execute(
        CreatePlanCommand(
            slug=body.slug,
            name=body.name,
            description=body.description,
            monthly_price=body.monthly_price,
            annual_price=body.annual_price,
            document_limit=body.document_limit,
            limit_cycle=body.limit_cycle,
            max_locations=body.max_locations,
            max_emission_points=body.max_emission_points,
            max_users=body.max_users,
            pruebas_monthly_docs_limit=body.pruebas_monthly_docs_limit,
            pruebas_monthly_bulk_limit=body.pruebas_monthly_bulk_limit,
            dedicated_queue=body.dedicated_queue,
            self_service=body.self_service,
            includes_credit_notes=body.includes_credit_notes,
            includes_withholdings=body.includes_withholdings,
            includes_delivery_notes=body.includes_delivery_notes,
            includes_api=body.includes_api,
            order=body.order,
            created_by=request.user_id,
        )
    )
    response = ApiResponse.created(plan.to_dict(), request.request_id)
    repo.commit(
        plan=plan,
        user_id=request.user_id,
        action="CREATE",
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_superadmin
def _admin_list(request: Request, context) -> dict:
    query = _parse_list_query(request.query_params)
    plans = ListPlansUseCase(_repo()).execute(query)
    return ApiResponse.ok({"items": [p.to_dict() for p in plans]}, request.request_id)


@lambda_handler
@require_superadmin
def _admin_get(request: Request, context) -> dict:
    slug = require_path_param(request, "id")
    plan = GetPlanBySlugUseCase(_repo()).execute(slug)
    return ApiResponse.ok(plan.to_dict(), request.request_id)


@public_lambda_handler
def _list(request: Request, context) -> dict:
    plans = ListPlansUseCase(_repo()).execute(ListPlansQuery(status="active"))
    return ApiResponse.ok({"items": [p.to_dict() for p in plans]}, request.request_id)


@public_lambda_handler
def _get(request: Request, context) -> dict:
    slug = require_path_param(request, "id")
    plan = GetPlanBySlugUseCase(_repo()).execute(slug)
    if not plan.active:
        raise PlanNotFoundError()
    return ApiResponse.ok(plan.to_dict(), request.request_id)


@lambda_handler
@require_superadmin
@idempotent
def _update(request: Request, context) -> dict:
    plan_id = require_path_param(request, "id")
    body = parse(UpdatePlanRequest, request.body)
    repo = _repo()
    plan = UpdatePlanUseCase(repo).execute(
        UpdatePlanCommand(
            id=plan_id,
            updated_by=request.user_id,
            name=body.name,
            description=body.description,
            monthly_price=body.monthly_price,
            annual_price=body.annual_price,
            document_limit=body.document_limit,
            limit_cycle=body.limit_cycle,
            max_locations=body.max_locations,
            max_emission_points=body.max_emission_points,
            max_users=body.max_users,
            pruebas_monthly_docs_limit=body.pruebas_monthly_docs_limit,
            pruebas_monthly_bulk_limit=body.pruebas_monthly_bulk_limit,
            dedicated_queue=body.dedicated_queue,
            self_service=body.self_service,
            includes_credit_notes=body.includes_credit_notes,
            includes_withholdings=body.includes_withholdings,
            includes_delivery_notes=body.includes_delivery_notes,
            includes_api=body.includes_api,
            order=body.order,
        )
    )
    response = ApiResponse.ok(plan.to_dict(), request.request_id)
    repo.commit(
        plan=plan,
        user_id=request.user_id,
        action="UPDATE",
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_superadmin
@idempotent
def _toggle(request: Request, context) -> dict:
    plan_id = require_path_param(request, "id")
    body = parse(TogglePlanRequest, request.body)
    repo = _repo()
    plan = TogglePlanUseCase(repo).execute(
        TogglePlanCommand(
            id=plan_id,
            active=body.active,
            updated_by=request.user_id,
        )
    )
    response = ApiResponse.ok(plan.to_dict(), request.request_id)
    repo.commit(
        plan=plan,
        user_id=request.user_id,
        action="STATUS",
        idempotency=require_current_context(),
        response=response,
    )
    return response


# ── Entry point AWS ───────────────────────────────────────────────────────────

_ID_PATTERN = re.compile(r"^/plans/[^/]+$")
_STATUS_PATTERN = re.compile(r"^/plans/[^/]+/status$")
_ADMIN_ID_PATTERN = re.compile(r"^/superadmin/plans/[^/]+$")


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path = ctx.get("http", {}).get("path", "")

    if path == "/superadmin/plans":
        if method == "GET":
            return _admin_list(event, context)

    if _ADMIN_ID_PATTERN.match(path):
        if method == "GET":
            return _admin_get(event, context)

    if path == "/plans":
        if method == "POST":
            return _create(event, context)
        if method == "GET":
            return _list(event, context)

    if _STATUS_PATTERN.match(path):
        if method == "PATCH":
            return _toggle(event, context)

    if _ID_PATTERN.match(path):
        if method == "GET":
            return _get(event, context)
        if method == "PATCH":
            return _update(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
