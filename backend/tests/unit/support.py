from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from lambdas.clients.domain.commands import CreateClientCommand
from lambdas.clients.domain.entity import Client
from lambdas.clients.domain.errors import ClientNotFoundError
from lambdas.tenants.domain.commands import CreateTenantCommand
from lambdas.tenants.domain.tenant import Tenant
from shared.errors import ValidationError

VALID_RUC = "1792146739001"


class LambdaContext:
    function_name = "unit-test"


def configure_unit_environment() -> None:
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_DEFAULT_REGION", "sa-east-1")
    os.environ.setdefault("AWS_REGION", "sa-east-1")
    os.environ.setdefault("LOG_LEVEL", "CRITICAL")


def tenant_payload(**overrides: Any) -> dict:
    payload = {
        "ruc": VALID_RUC,
        "trade_name": "CodeLabs Test",
        "legal_name": "CodeLabs Test S.A.",
        "legal_rep_name": "Francis Ulloa",
        "email": "OWNER@CODELABS.COM",
        "phone": "0999999999",
        "address": "Av Siempre Viva 123",
        "accounting_required": False,
        "plan_id": "uuid-basic",
    }
    payload.update(overrides)
    return payload


def create_tenant_command(**overrides: Any) -> CreateTenantCommand:
    payload = tenant_payload()
    payload.update(
        {
            "created_by": "user-1",
            **overrides,
        }
    )
    return CreateTenantCommand(**payload)


def make_tenant(*, plan_limit_cycle: str = "month", **overrides: Any) -> Tenant:
    tenant = Tenant.create(create_tenant_command(), plan_limit_cycle=plan_limit_cycle)
    for key, value in overrides.items():
        setattr(tenant, key, value)
    return tenant


def client_payload(**overrides: Any) -> dict:
    payload = {
        "identification": VALID_RUC,
        "identification_type": "ruc",
        "person_type": "juridica",
        "legal_name": "CodeLabs Cliente S.A.",
        "trade_name": "Cliente Test",
        "special_taxpayer": False,
        "emails": ["CLIENTE@CODELABS.COM"],
        "phones": ["0999999999"],
        "addresses": [{"label": "Matriz", "line": "Av Siempre Viva 456", "city": "Quito"}],
    }
    payload.update(overrides)
    return payload


def create_client_command(**overrides: Any) -> CreateClientCommand:
    payload = client_payload()
    payload.update(
        {
            "tenant_id": "tenant-1",
            "created_by": "user-1",
            **overrides,
        }
    )
    return CreateClientCommand(**payload)


def make_client(**overrides: Any) -> Client:
    client = Client.create(create_client_command())
    for key, value in overrides.items():
        setattr(client, key, value)
    return client


def api_event(
    *,
    method: str,
    path: str,
    body: dict | None = None,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
    claims: dict[str, str] | None = None,
    path_params: dict[str, str] | None = None,
) -> dict:
    base_claims = {
        "sub": "user-1",
        "custom:tenant_id": "",
        "custom:role": "superadmin",
        "custom:is_superadmin": "true",
    }
    if claims:
        base_claims.update(claims)

    if path_params is None:
        # Extrae {id} para cualquier patrón /{resource}/{id}[/sub]
        path_params = {}
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            path_params["id"] = parts[1]

    return {
        "version": "2.0",
        "rawPath": path,
        "requestContext": {
            "requestId": "req-1",
            "http": {"method": method, "path": path},
            "authorizer": {"jwt": {"claims": base_claims}},
        },
        "headers": {k.lower(): v for k, v in (headers or {}).items()},
        "queryStringParameters": query or None,
        "pathParameters": path_params or None,
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }


def decode_response(response: dict) -> dict:
    return json.loads(response["body"])


class FakeTenantRepository:
    def __init__(self) -> None:
        self.tenants: dict[str, Tenant] = {}
        self.existing_by_ruc: Tenant | None = None
        self.list_result: tuple[list[Tenant], str | None] = ([], None)
        self.certificate_expiry_due: list[Tenant] = []
        self.list_with_certificate_expiry_due_calls: list[datetime] = []
        self.save_calls: list[tuple[Tenant, str]] = []
        self.commit_calls: list[dict[str, Any]] = []
        self.commit_admin_events_calls: list[dict[str, Any]] = []
        self.get_by_ruc_calls: list[str] = []
        self.list_calls: list[dict[str, Any]] = []
        self.get_by_id_calls: list[str] = []
        # Exceptions to raise on successive commit() calls before succeeding,
        # e.g. [OptimisticLockError()] retries once then commits normally.
        self.commit_errors: list[Exception] = []
        # Errors to raise on save() for a given tenant id, e.g.
        # {"tenant-1": OptimisticLockError()}.
        self.save_errors: dict[str, Exception] = {}

    def get_by_id(self, tenant_id: str) -> Tenant:
        from lambdas.tenants.domain.errors import TenantNotFoundError

        self.get_by_id_calls.append(tenant_id)
        if tenant_id not in self.tenants:
            raise TenantNotFoundError()
        return self.tenants[tenant_id]

    def get_by_ruc(self, ruc: str) -> Tenant | None:
        self.get_by_ruc_calls.append(ruc)
        return self.existing_by_ruc

    def save(self, tenant: Tenant, user_id: str) -> None:
        self.save_calls.append((tenant, user_id))
        if tenant.id in self.save_errors:
            raise self.save_errors.pop(tenant.id)
        self.tenants[tenant.id] = tenant

    def list(
        self,
        limit: int,
        next_token: str | None,
        status: str | None = None,
        q: str | None = None,
        ruc: str | None = None,
        sri_environment: str | None = None,
        plan_status: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> tuple[list[Tenant], str | None]:
        self.list_calls.append(
            {
                "limit": limit,
                "next_token": next_token,
                "status": status,
                "q": q,
                "ruc": ruc,
                "sri_environment": sri_environment,
                "plan_status": plan_status,
                "created_from": created_from,
                "created_to": created_to,
            }
        )
        return self.list_result

    def commit(self, **kwargs: Any) -> None:
        self.commit_calls.append(kwargs)
        if self.commit_errors:
            raise self.commit_errors.pop(0)
        tenant = kwargs["tenant"]
        self.tenants[tenant.id] = tenant

    def commit_admin_events(self, **kwargs: Any) -> None:
        self.commit_admin_events_calls.append(kwargs)
        if self.commit_errors:
            raise self.commit_errors.pop(0)

    def list_with_certificate_expiry_due(self, before: datetime) -> list[Tenant]:
        self.list_with_certificate_expiry_due_calls.append(before)
        return self.certificate_expiry_due


class FakePlanCatalog:
    def __init__(self, *, active: bool = True, exists: bool = True) -> None:
        self.active = active
        self.exists = exists
        self.checked_ids: list[str] = []

    def ensure_active(self, plan_id: str) -> None:
        self.checked_ids.append(plan_id)
        if not plan_id or not self.exists:
            raise ValidationError("plan_id inválido")
        if not self.active:
            raise ValidationError("plan_id no está activo")


class FakeClientRepository:
    def __init__(self) -> None:
        self.clients: dict[str, Client] = {}
        self.existing_by_identification: Client | None = None
        self.list_result: tuple[list[Client], str | None] = ([], None)
        self.commit_calls: list[dict[str, Any]] = []
        self.get_by_identification_calls: list[tuple[str, str | None]] = []
        self.list_calls: list[dict[str, Any]] = []
        self.commit_error: Exception | None = None

    def get_by_id(self, client_id: str) -> Client:
        if client_id not in self.clients:
            raise ClientNotFoundError()
        return self.clients[client_id]

    def get_by_identification(
        self,
        identification: str,
        exclude_id: str | None = None,
    ) -> Client | None:
        self.get_by_identification_calls.append((identification, exclude_id))
        if (
            self.existing_by_identification is not None
            and self.existing_by_identification.id != exclude_id
        ):
            return self.existing_by_identification
        return None

    def list(
        self,
        limit: int,
        next_token: str | None,
        status: str | None = None,
        q: str | None = None,
        identification: str | None = None,
        identification_type: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> tuple[list[Client], str | None]:
        self.list_calls.append(
            {
                "limit": limit,
                "next_token": next_token,
                "status": status,
                "q": q,
                "identification": identification,
                "identification_type": identification_type,
                "created_from": created_from,
                "created_to": created_to,
            }
        )
        return self.list_result

    def save(self, client: Client, user_id: str) -> None:
        self.clients[client.id] = client

    def commit(self, **kwargs: Any) -> None:
        if self.commit_error:
            raise self.commit_error
        self.commit_calls.append(kwargs)
        self.clients[kwargs["client"].id] = kwargs["client"]
