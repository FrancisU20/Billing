from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository


class ListPlansUseCase:
    def __init__(self, repo: IPlanRepository) -> None:
        self._repo = repo

    def execute(self, active_only: bool = True) -> list[Plan]:
        plans = self._repo.list(active_only=active_only)
        return sorted(plans, key=lambda p: p.order)
