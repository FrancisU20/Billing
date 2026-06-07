from __future__ import annotations

from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository


class GetPlanBySlugUseCase:
    """Public lookup by slug — GET /plans/{slug} route."""

    def __init__(self, repo: IPlanRepository) -> None:
        self._repo = repo

    def execute(self, slug: str) -> Plan:
        return self._repo.get_by_slug(slug)
