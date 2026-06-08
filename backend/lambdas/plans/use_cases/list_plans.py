from __future__ import annotations

from dataclasses import dataclass

from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository


@dataclass(frozen=True)
class ListPlansQuery:
    status: str | None = None
    slug: str | None = None
    q: str | None = None
    limit_cycle: str | None = None
    created_from: str | None = None
    created_to: str | None = None


class ListPlansUseCase:
    def __init__(self, repo: IPlanRepository) -> None:
        self._repo = repo

    def execute(self, query: ListPlansQuery) -> list[Plan]:
        plans = self._repo.list(
            status=query.status,
            slug=query.slug,
            q=query.q,
            limit_cycle=query.limit_cycle,
            created_from=query.created_from,
            created_to=query.created_to,
        )
        return sorted(plans, key=lambda p: p.order)
