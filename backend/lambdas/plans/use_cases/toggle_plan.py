from lambdas.plans.domain.commands import TogglePlanCommand
from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository


class TogglePlanUseCase:
    def __init__(self, repo: IPlanRepository) -> None:
        self._repo = repo

    def execute(self, cmd: TogglePlanCommand) -> Plan:
        plan = self._repo.get_by_id(cmd.id)
        plan.toggle(cmd.active, cmd.updated_by)
        self._repo.save(plan)
        return plan
