from __future__ import annotations

from dataclasses import dataclass

from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant


@dataclass(frozen=True)
class ListTenantsQuery:
    limit: int = 20
    next_token: str | None = None
    status: str | None = None
    q: str | None = None
    ruc: str | None = None
    sri_environment: str | None = None
    plan_status: str | None = None
    created_from: str | None = None
    created_to: str | None = None


class ListTenantsUseCase:
    def __init__(self, repo: ITenantRepository) -> None:
        self._repo = repo

    def execute(self, query: ListTenantsQuery) -> tuple[list[Tenant], str | None]:
        return self._repo.list(
            limit=query.limit,
            next_token=query.next_token,
            status=query.status,
            q=query.q,
            ruc=query.ruc,
            sri_environment=query.sri_environment,
            plan_status=query.plan_status,
            created_from=query.created_from,
            created_to=query.created_to,
        )
