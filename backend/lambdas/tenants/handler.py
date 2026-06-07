"""
Lambda de Tenants — entry point AWS.

Rutas:
    POST   /tenants               crear tenant          (superadmin)
    GET    /tenants               listar todos          (superadmin)
    GET    /tenants/{id}          obtener por ID        (superadmin | miembros del tenant)
    PATCH  /tenants/{id}          actualizar            (superadmin | owner | admin)
    PATCH  /tenants/{id}/status   cambiar estado        (superadmin)
    DELETE /tenants/{id}          eliminar (soft)       (superadmin)

El routing usa routeKey de HTTP API Gateway (ej. "POST /tenants").
Para local dev, el servidor uvicorn construye routeKey manualmente.

Inicialización cold start: clientes boto3 y repositorio se crean fuera del handler.
"""
import re

from lambdas._base.handler import lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse
from lambdas._base.permissions import require_role
from lambdas._base.response import ApiResponse
from lambdas.tenants.domain.commands import (
    CreateTenantCommand,
    ToggleStatusCommand,
    UpdateTenantCommand,
)
from lambdas.tenants.domain.enums import EstadoTenant
from lambdas.tenants.infra.tenant_repository import DynamoTenantRepository
from lambdas.tenants.schemas import (
    CreateTenantRequest,
    ToggleStatusRequest,
    UpdateTenantRequest,
)
from lambdas.tenants.use_cases.create_tenant import CreateTenantUseCase
from lambdas.tenants.use_cases.delete_tenant import DeleteTenantUseCase
from lambdas.tenants.use_cases.get_tenant import GetTenantUseCase
from lambdas.tenants.use_cases.list_tenants import ListTenantsQuery, ListTenantsUseCase
from lambdas.tenants.use_cases.toggle_status import ToggleStatusUseCase
from lambdas.tenants.use_cases.update_tenant import UpdateTenantUseCase
from shared.config import env
from shared.db.client import get_table
from shared.errors import ForbiddenError, NotFoundError, ValidationError

# ── Cold start — inicializado una sola vez por contenedor ─────────────────────
_TABLE            = get_table("TENANTS_TABLE")
_audit_table_name = env("AUDIT_LOG_TABLE", "")
_AUDIT_TABLE      = get_table("AUDIT_LOG_TABLE") if _audit_table_name else None
_outbox_table_name = env("OUTBOX_TABLE", "")
_OUTBOX_TABLE      = get_table("OUTBOX_TABLE") if _outbox_table_name else None

# ── Factory del repositorio por request (inyecta tenant_id del JWT) ───────────
def _repo():
    return DynamoTenantRepository(_TABLE, _AUDIT_TABLE, _OUTBOX_TABLE)


def _parse_list_query(query_params: dict) -> ListTenantsQuery:
    raw_limit = query_params.get("limit", 20)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError) as exc:
        raise ValidationError("limit debe ser un número entero") from exc

    if limit < 1:
        raise ValidationError("limit debe ser mayor a cero")

    estado = query_params.get("estado")
    if estado:
        try:
            EstadoTenant(estado)
        except ValueError as exc:
            raise ValidationError("estado inválido") from exc

    return ListTenantsQuery(
        limit      = min(limit, 100),
        next_token = query_params.get("next_token"),
        estado     = estado,
    )


# ── Handlers por operación ────────────────────────────────────────────────────

@lambda_handler
@require_role("superadmin")
@idempotent
def _create(request: Request, context) -> dict:
    body    = parse(CreateTenantRequest, request.body)
    command = CreateTenantCommand(
        ruc              = body.ruc,
        nombre_comercial = body.nombre_comercial,
        nombre_rep_legal = body.nombre_rep_legal,
        email            = body.email,
        telefono         = body.telefono,
        direccion        = body.direccion,
        plan             = body.plan,
        created_by       = request.user_id,
    )
    repo = _repo()
    tenant, events = CreateTenantUseCase(repo).execute(command)
    response = ApiResponse.created(tenant.to_dict(), request.request_id)
    repo.commit(
        tenant      = tenant,
        user_id     = request.user_id,
        action      = "CREATE",
        events      = events,
        idempotency = require_current_context(),
        response    = response,
    )
    return response


@lambda_handler
@require_role("superadmin")
def _list(request: Request, context) -> dict:
    query = _parse_list_query(request.query_params)
    tenants, next_token = ListTenantsUseCase(_repo()).execute(query)
    return ApiResponse.paginated(
        items      = [t.to_dict() for t in tenants],
        next_token = next_token,
        request_id = request.request_id,
    )


@lambda_handler
def _get(request: Request, context) -> dict:
    tenant_id = request.path_params.get("id", "")

    # superadmin puede ver cualquier tenant; miembros solo el suyo
    if not request.is_superadmin and request.tenant_id != tenant_id:
        raise ForbiddenError()

    tenant = GetTenantUseCase(_repo()).execute(tenant_id)
    return ApiResponse.ok(tenant.to_dict(), request.request_id)


@lambda_handler
@require_role("owner", "admin", "superadmin")
@idempotent
def _update(request: Request, context) -> dict:
    tenant_id = request.path_params.get("id", "")

    # Non-superadmin solo puede actualizar su propio tenant
    if not request.is_superadmin and request.tenant_id != tenant_id:
        raise ForbiddenError()

    body    = parse(UpdateTenantRequest, request.body)
    command = UpdateTenantCommand(
        tenant_id        = tenant_id,
        updated_by       = request.user_id,
        nombre_comercial = body.nombre_comercial,
        nombre_rep_legal = body.nombre_rep_legal,
        email            = body.email,
        telefono         = body.telefono,
        direccion        = body.direccion,
        ambiente_sri     = body.ambiente_sri,
    )
    repo = _repo()
    tenant, events = UpdateTenantUseCase(repo).execute(command)
    response = ApiResponse.ok(tenant.to_dict(), request.request_id)
    repo.commit(
        tenant      = tenant,
        user_id     = request.user_id,
        action      = "UPDATE",
        events      = events,
        idempotency = require_current_context(),
        response    = response,
    )
    return response


@lambda_handler
@require_role("superadmin")
@idempotent
def _toggle_status(request: Request, context) -> dict:
    tenant_id = request.path_params.get("id", "")
    body      = parse(ToggleStatusRequest, request.body)
    command   = ToggleStatusCommand(
        tenant_id    = tenant_id,
        nuevo_estado = body.estado,
        updated_by   = request.user_id,
    )
    repo = _repo()
    tenant, events = ToggleStatusUseCase(repo).execute(command)
    response = ApiResponse.ok(tenant.to_dict(), request.request_id)
    repo.commit(
        tenant      = tenant,
        user_id     = request.user_id,
        action      = "STATUS",
        events      = events,
        idempotency = require_current_context(),
        response    = response,
    )
    return response


@lambda_handler
@require_role("superadmin")
@idempotent
def _delete(request: Request, context) -> dict:
    tenant_id = request.path_params.get("id", "")
    repo = _repo()
    tenant, events = DeleteTenantUseCase(repo).execute(tenant_id, request.user_id)
    response = ApiResponse.no_content(request.request_id)
    repo.commit(
        tenant      = tenant,
        user_id     = request.user_id,
        action      = "DELETE",
        events      = events,
        idempotency = require_current_context(),
        response    = response,
    )
    return response


# ── Entry point AWS ───────────────────────────────────────────────────────────

_ID_PATTERN     = re.compile(r"^/tenants/[^/]+$")
_STATUS_PATTERN = re.compile(r"^/tenants/[^/]+/status$")


def handler(event: dict, context) -> dict:
    ctx    = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path   = ctx.get("http", {}).get("path", "")

    if path == "/tenants":
        if method == "POST": return _create(event, context)
        if method == "GET":  return _list(event, context)

    if _STATUS_PATTERN.match(path):
        if method == "PATCH": return _toggle_status(event, context)

    if _ID_PATTERN.match(path):
        if method == "GET":    return _get(event, context)
        if method == "PATCH":  return _update(event, context)
        if method == "DELETE": return _delete(event, context)

    request_id = ctx.get("requestId", "local")
    return ApiResponse.error(NotFoundError(), request_id)
