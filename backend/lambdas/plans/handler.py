"""
Plans Lambda — AWS entry point.

Routes:
    POST   /plans              create plan            (superadmin)
    GET    /plans              list plans             (public — no auth)
    GET    /plans/{slug}       get by slug            (public — no auth)
    PATCH  /plans/{id}         update by UUID         (superadmin)
    PATCH  /plans/{id}/status  activate/deactivate    (superadmin)

GET is public so the frontend can render the pricing table without login.
Mutations use the UUID (id) — stable even if the slug changes.
"""
import re

from lambdas._base.handler import lambda_handler, public_lambda_handler
from lambdas._base.parser import Request, parse
from lambdas._base.permissions import require_role
from lambdas._base.response import ApiResponse
from lambdas.plans.domain.commands import (
    CreatePlanCommand,
    TogglePlanCommand,
    UpdatePlanCommand,
)
from lambdas.plans.infra.plan_repository import DynamoPlanRepository
from lambdas.plans.schemas import CreatePlanRequest, TogglePlanRequest, UpdatePlanRequest
from lambdas.plans.use_cases.create_plan import CreatePlanUseCase
from lambdas.plans.use_cases.get_plan import GetPlanBySlugUseCase
from lambdas.plans.use_cases.list_plans import ListPlansUseCase
from lambdas.plans.use_cases.toggle_plan import TogglePlanUseCase
from lambdas.plans.use_cases.update_plan import UpdatePlanUseCase
from shared.db.client import get_table
from shared.errors import NotFoundError

_table = get_table("PLANS_TABLE")


def _repo() -> DynamoPlanRepository:
    return DynamoPlanRepository(_table)


# ── Handlers ──────────────────────────────────────────────────────────────────

@lambda_handler
@require_role("superadmin")
def _create(request: Request, context) -> dict:
    body = parse(CreatePlanRequest, request.body)
    plan = CreatePlanUseCase(_repo()).execute(CreatePlanCommand(
        slug                    = body.slug,
        name                    = body.name,
        description             = body.description,
        monthly_price           = body.monthly_price,
        annual_price            = body.annual_price,
        document_limit          = body.document_limit,
        limit_cycle             = body.limit_cycle,
        max_locations           = body.max_locations,
        max_emission_points     = body.max_emission_points,
        max_users               = body.max_users,
        includes_credit_notes   = body.includes_credit_notes,
        includes_withholdings   = body.includes_withholdings,
        includes_delivery_notes = body.includes_delivery_notes,
        includes_api            = body.includes_api,
        order                   = body.order,
        created_by              = request.user_id,
    ))
    return ApiResponse.created(plan.to_dict(), request.request_id)


@public_lambda_handler
def _list(request: Request, context) -> dict:
    active_only = request.query_params.get("active", "true").lower() != "false"
    plans       = ListPlansUseCase(_repo()).execute(active_only=active_only)
    return ApiResponse.ok({"items": [p.to_dict() for p in plans]}, request.request_id)


@public_lambda_handler
def _get(request: Request, context) -> dict:
    slug = request.path_params.get("id", "")  # APIGW path param is named {id}
    plan = GetPlanBySlugUseCase(_repo()).execute(slug)
    return ApiResponse.ok(plan.to_dict(), request.request_id)


@lambda_handler
@require_role("superadmin")
def _update(request: Request, context) -> dict:
    plan_id = request.path_params.get("id", "")
    body    = parse(UpdatePlanRequest, request.body)
    plan    = UpdatePlanUseCase(_repo()).execute(UpdatePlanCommand(
        id                      = plan_id,
        updated_by              = request.user_id,
        name                    = body.name,
        description             = body.description,
        monthly_price           = body.monthly_price,
        annual_price            = body.annual_price,
        document_limit          = body.document_limit,
        limit_cycle             = body.limit_cycle,
        max_locations           = body.max_locations,
        max_emission_points     = body.max_emission_points,
        max_users               = body.max_users,
        includes_credit_notes   = body.includes_credit_notes,
        includes_withholdings   = body.includes_withholdings,
        includes_delivery_notes = body.includes_delivery_notes,
        includes_api            = body.includes_api,
        order                   = body.order,
    ))
    return ApiResponse.ok(plan.to_dict(), request.request_id)


@lambda_handler
@require_role("superadmin")
def _toggle(request: Request, context) -> dict:
    plan_id = request.path_params.get("id", "")
    body    = parse(TogglePlanRequest, request.body)
    plan    = TogglePlanUseCase(_repo()).execute(TogglePlanCommand(
        id         = plan_id,
        active     = body.active,
        updated_by = request.user_id,
    ))
    return ApiResponse.ok(plan.to_dict(), request.request_id)


# ── Entry point AWS ───────────────────────────────────────────────────────────

_ID_PATTERN     = re.compile(r"^/plans/[^/]+$")
_STATUS_PATTERN = re.compile(r"^/plans/[^/]+/status$")


def handler(event: dict, context) -> dict:
    ctx    = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path   = ctx.get("http", {}).get("path", "")

    if path == "/plans":
        if method == "POST": return _create(event, context)
        if method == "GET":  return _list(event, context)

    if _STATUS_PATTERN.match(path):
        if method == "PATCH": return _toggle(event, context)

    if _ID_PATTERN.match(path):
        if method == "GET":   return _get(event, context)
        if method == "PATCH": return _update(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
