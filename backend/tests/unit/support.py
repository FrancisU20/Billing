from __future__ import annotations

import json
import os
from typing import Any

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
        "legal_rep_name": "Francis Ulloa",
        "email": "OWNER@CODELABS.COM",
        "phone": "0999999999",
        "address": "Av Siempre Viva 123",
        "plan_id": "uuid-basic",
    }
    payload.update(overrides)
    return payload


def create_tenant_command(**overrides: Any) -> CreateTenantCommand:
    payload = tenant_payload()
    payload.update({
        "created_by": "user-1",
        **overrides,
    })
    return CreateTenantCommand(**payload)


def make_tenant(**overrides: Any) -> Tenant:
    tenant = Tenant.create(create_tenant_command())
    for key, value in overrides.items():
        setattr(tenant, key, value)
    return tenant


def api_event(
    *,
    method: str,
    path: str,
    body: dict | None = None,
    headers: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
    claims: dict[str, str] | None = None,
) -> dict:
    base_claims = {
        "sub": "user-1",
        "custom:tenant_id": "",
        "custom:role": "superadmin",
        "custom:is_superadmin": "true",
    }
    if claims:
        base_claims.update(claims)

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
        self.save_calls: list[tuple[Tenant, str]] = []
        self.commit_calls: list[dict[str, Any]] = []
        self.get_by_ruc_calls: list[str] = []

    def get_by_id(self, tenant_id: str) -> Tenant:
        from lambdas.tenants.domain.errors import TenantNotFoundError
        if tenant_id not in self.tenants:
            raise TenantNotFoundError()
        return self.tenants[tenant_id]

    def get_by_ruc(self, ruc: str) -> Tenant | None:
        self.get_by_ruc_calls.append(ruc)
        return self.existing_by_ruc

    def save(self, tenant: Tenant, user_id: str) -> None:
        self.save_calls.append((tenant, user_id))
        self.tenants[tenant.id] = tenant

    def list(
        self,
        limit: int,
        next_token: str | None,
        status: str | None = None,
    ) -> tuple[list[Tenant], str | None]:
        return self.list_result

    def commit(self, **kwargs: Any) -> None:
        self.commit_calls.append(kwargs)
        tenant = kwargs["tenant"]
        self.tenants[tenant.id] = tenant


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
