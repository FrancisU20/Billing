from __future__ import annotations

"""
Clients Lambda — AWS entry point.

Routes:
    POST   /clients       create client   (owner | admin)
    GET    /clients       list clients    (owner | admin | viewer)
    GET    /clients/{id}  get by ID       (owner | admin | viewer)
    PATCH  /clients/{id}  update          (owner | admin)
    DELETE /clients/{id}  soft delete     (owner | admin)
"""
import re

from lambdas._base.handler import lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse, require_path_param
from lambdas._base.permissions import require_role
from lambdas._base.response import ApiResponse
from lambdas.clients.domain.commands import (
    AddressCommand,
    CreateClientCommand,
    UpdateClientCommand,
)
from lambdas.clients.domain.enums import ClientStatus, IdentificationType
from lambdas.clients.infra.client_repository import DynamoClientRepository
from lambdas.clients.schemas import CreateClientRequest, UpdateClientRequest
from lambdas.clients.use_cases.create_client import CreateClientUseCase
from lambdas.clients.use_cases.delete_client import DeleteClientUseCase
from lambdas.clients.use_cases.get_client import GetClientUseCase
from lambdas.clients.use_cases.list_clients import ListClientsQuery, ListClientsUseCase
from lambdas.clients.use_cases.update_client import UpdateClientUseCase
from shared.config import env
from shared.dates import parse_date_boundary
from shared.db.client import get_table
from shared.db.limits import DEFAULT_LIST_LIMIT, clamp_list_limit
from shared.errors import MissingTenantContextError, NotFoundError, ValidationError

_TABLE = get_table("CLIENTS_TABLE")
_AUDIT_TABLE = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None


def _repo(request: Request) -> DynamoClientRepository:
    if not request.tenant_id:
        raise MissingTenantContextError()
    return DynamoClientRepository(request.tenant_id, _TABLE, _AUDIT_TABLE)


def _address_commands(addresses) -> list[AddressCommand]:
    return [AddressCommand(label=a.label, line=a.line, city=a.city) for a in addresses]


def _parse_list_query(params: dict) -> ListClientsQuery:
    try:
        limit = int(params.get("limit", DEFAULT_LIST_LIMIT))
    except (TypeError, ValueError) as exc:
        raise ValidationError("limit debe ser un número entero") from exc
    if limit < 1:
        raise ValidationError("limit debe ser mayor a cero")

    status = params.get("status")
    if status:
        try:
            ClientStatus(status)
        except ValueError as exc:
            raise ValidationError("Estado inválido") from exc

    identification_type = params.get("identification_type")
    if identification_type:
        try:
            IdentificationType(identification_type)
        except ValueError as exc:
            raise ValidationError("Tipo de identificación inválido") from exc

    return ListClientsQuery(
        limit=clamp_list_limit(limit),
        next_token=params.get("next_token"),
        status=status,
        q=params.get("q"),
        identification=params.get("identification"),
        identification_type=identification_type,
        created_from=parse_date_boundary(params.get("created_from"), end_of_day=False),
        created_to=parse_date_boundary(params.get("created_to"), end_of_day=True),
    )


@lambda_handler
@require_role("owner", "admin")
@idempotent
def _create(request: Request, context) -> dict:
    body = parse(CreateClientRequest, request.body)
    repo = _repo(request)
    client = CreateClientUseCase(repo).execute(
        CreateClientCommand(
            tenant_id=request.tenant_id,
            identification=body.identification,
            identification_type=body.identification_type,
            person_type=body.person_type,
            legal_name=body.legal_name,
            trade_name=body.trade_name,
            special_taxpayer=body.special_taxpayer,
            emails=body.emails,
            phones=body.phones,
            addresses=_address_commands(body.addresses),
            created_by=request.user_id,
        )
    )
    response = ApiResponse.created(client.to_dict(), request.request_id)
    repo.commit(
        client=client,
        user_id=request.user_id,
        action="CREATE",
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_role("owner", "admin", "viewer")
def _list(request: Request, context) -> dict:
    query = _parse_list_query(request.query_params)
    clients, next_token = ListClientsUseCase(_repo(request)).execute(query)
    return ApiResponse.paginated(
        items=[c.to_dict() for c in clients],
        next_token=next_token,
        request_id=request.request_id,
    )


@lambda_handler
@require_role("owner", "admin", "viewer")
def _get(request: Request, context) -> dict:
    client_id = require_path_param(request, "id")
    client = GetClientUseCase(_repo(request)).execute(client_id)
    return ApiResponse.ok(client.to_dict(), request.request_id)


@lambda_handler
@require_role("owner", "admin")
@idempotent
def _update(request: Request, context) -> dict:
    client_id = require_path_param(request, "id")
    body = parse(UpdateClientRequest, request.body)
    repo = _repo(request)
    client = UpdateClientUseCase(repo).execute(
        UpdateClientCommand(
            client_id=client_id,
            identification=body.identification,
            identification_type=body.identification_type,
            person_type=body.person_type,
            legal_name=body.legal_name,
            trade_name=body.trade_name,
            special_taxpayer=body.special_taxpayer,
            emails=body.emails,
            phones=body.phones,
            addresses=_address_commands(body.addresses) if body.addresses is not None else None,
            status=body.status,
            updated_by=request.user_id,
        )
    )
    response = ApiResponse.ok(client.to_dict(), request.request_id)
    repo.commit(
        client=client,
        user_id=request.user_id,
        action="UPDATE",
        idempotency=require_current_context(),
        response=response,
    )
    return response


@lambda_handler
@require_role("owner", "admin")
@idempotent
def _delete(request: Request, context) -> dict:
    client_id = require_path_param(request, "id")
    repo = _repo(request)
    client = DeleteClientUseCase(repo).execute(client_id, request.user_id)
    response = ApiResponse.no_content(request.request_id)
    repo.commit(
        client=client,
        user_id=request.user_id,
        action="DELETE",
        idempotency=require_current_context(),
        response=response,
    )
    return response


_ID_PATTERN = re.compile(r"^/clients/[^/]+$")


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    method = ctx.get("http", {}).get("method", "")
    path = ctx.get("http", {}).get("path", "")

    if path == "/clients":
        if method == "POST":
            return _create(event, context)
        if method == "GET":
            return _list(event, context)

    if _ID_PATTERN.match(path):
        if method == "GET":
            return _get(event, context)
        if method == "PATCH":
            return _update(event, context)
        if method == "DELETE":
            return _delete(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
