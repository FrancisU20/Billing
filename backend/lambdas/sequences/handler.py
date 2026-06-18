from __future__ import annotations

"""
Sequences Lambda — establishment and emission point management.

Routes:
    GET    /tenants/{id}/establishments                                → list_establishments
    POST   /tenants/{id}/establishments                                → create_establishment
    POST   /tenants/{id}/establishments/{code}/emission-points         → add_emission_point
    PATCH  /tenants/{id}/establishments/{code}/emission-points/{point} → edit_emission_point

Auth:
    - GET: owner, admin, viewer, superadmin
    - POST/PATCH: owner, admin, superadmin
    Superadmin can access any tenant; others only their own.
"""

import re

from lambdas._base.handler import lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.permissions import require_role
from lambdas._base.response import ApiResponse
from lambdas.sequences.domain.commands import (
    AddEmissionPointCommand,
    CreateEstablishmentCommand,
    EditEmissionPointCommand,
)
from lambdas.sequences.infra.sequences_repository import DynamoSequencesRepository
from lambdas.sequences.schemas import (
    AddEmissionPointRequest,
    CreateEstablishmentRequest,
    EditEmissionPointRequest,
)
from lambdas.sequences.use_cases.add_emission_point import AddEmissionPointUseCase
from lambdas.sequences.use_cases.create_establishment import CreateEstablishmentUseCase
from lambdas.sequences.use_cases.edit_emission_point import EditEmissionPointUseCase
from lambdas.sequences.use_cases.list_establishments import ListEstablishmentsUseCase
from shared.db.client import get_table
from shared.errors import ForbiddenError, NotFoundError

_table = get_table("SEQUENCES_TABLE")


def _repo() -> DynamoSequencesRepository:
    return DynamoSequencesRepository(_table)


def _authorize_tenant(request: Request, tenant_id: str) -> None:
    if request.is_superadmin:
        return
    if request.tenant_id != tenant_id:
        raise ForbiddenError()


# ── Handlers ──────────────────────────────────────────────────────────────────


@lambda_handler
@require_role("owner", "admin", "viewer", "superadmin")
def _list(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    _authorize_tenant(request, tenant_id)
    establishments = ListEstablishmentsUseCase(_repo()).execute(tenant_id)
    return ApiResponse.ok(
        {"items": [e.to_dict() for e in establishments]},
        request.request_id,
    )


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _create(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    _authorize_tenant(request, tenant_id)
    body = parse(CreateEstablishmentRequest, request.body)
    repo = _repo()
    establishment = CreateEstablishmentUseCase(repo).execute(
        CreateEstablishmentCommand(
            tenant_id=tenant_id,
            code=body.code,
            label=body.label,
            created_by=request.user_id,
        )
    )
    response = ApiResponse.created(establishment.to_dict(), request.request_id)
    repo.commit(
        establishment=establishment,
        action="CREATE",
        user_id=request.user_id,
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _add_emission_point(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    establishment_code = require_path_param(request, "code")
    _authorize_tenant(request, tenant_id)
    body = parse(AddEmissionPointRequest, request.body)
    repo = _repo()
    result = AddEmissionPointUseCase(repo).execute(
        AddEmissionPointCommand(
            tenant_id=tenant_id,
            establishment_code=establishment_code,
            code=body.code,
            label=body.label,
            initial_sequential=body.initial_sequential,
            created_by=request.user_id,
        )
    )
    response = ApiResponse.created(result.establishment.to_dict(), request.request_id)
    repo.commit(
        establishment=result.establishment,
        action="ADD_EMISSION_POINT",
        user_id=request.user_id,
        new_emission_point=result.new_emission_point,
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _edit_emission_point(request: Request, context) -> dict:
    tenant_id = require_path_param(request, "id")
    establishment_code = require_path_param(request, "code")
    emission_point_code = require_path_param(request, "point")
    _authorize_tenant(request, tenant_id)
    body = parse(EditEmissionPointRequest, request.body)
    repo = _repo()
    result = EditEmissionPointUseCase(repo).execute(
        EditEmissionPointCommand(
            tenant_id=tenant_id,
            establishment_code=establishment_code,
            code=emission_point_code,
            label=body.label,
            initial_sequential=body.initial_sequential,
            updated_by=request.user_id,
        )
    )
    response = ApiResponse.ok(result.establishment.to_dict(), request.request_id)
    repo.commit(
        establishment=result.establishment,
        action="EDIT_EMISSION_POINT",
        user_id=request.user_id,
        update_sequence=result.update_sequence,
        idempotency=require_current_context(),
        response=response,
    )
    return response


# ── Entry point AWS ───────────────────────────────────────────────────────────

_ESTABLISHMENTS_PATTERN = re.compile(r"^/tenants/[^/]+/establishments$")
_EMISSION_POINTS_PATTERN = re.compile(r"^/tenants/[^/]+/establishments/[^/]+/emission-points$")
_EMISSION_POINT_PATTERN = re.compile(r"^/tenants/[^/]+/establishments/[^/]+/emission-points/[^/]+$")


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path = ctx.get("http", {}).get("path", "")

    if _ESTABLISHMENTS_PATTERN.match(path):
        if method == "GET":
            return _list(event, context)
        if method == "POST":
            return _create(event, context)

    if _EMISSION_POINTS_PATTERN.match(path):
        if method == "POST":
            return _add_emission_point(event, context)

    if _EMISSION_POINT_PATTERN.match(path):
        if method == "PATCH":
            return _edit_emission_point(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
