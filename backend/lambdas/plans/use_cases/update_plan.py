from __future__ import annotations
from decimal import Decimal

from lambdas.plans.domain.commands import UpdatePlanCommand
from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository
from shared.errors import ValidationError

_VALID_CYCLES = {"month", "year"}


class UpdatePlanUseCase:
    def __init__(self, repo: IPlanRepository) -> None:
        self._repo = repo

    def execute(self, cmd: UpdatePlanCommand) -> Plan:
        if cmd.limit_cycle is not None and cmd.limit_cycle not in _VALID_CYCLES:
            raise ValidationError("El ciclo de límite debe ser 'month' o 'year'.")
        if cmd.monthly_price is not None and cmd.monthly_price < Decimal("0"):
            raise ValidationError("Los precios no pueden ser negativos.")
        if cmd.annual_price is not None and cmd.annual_price < Decimal("0"):
            raise ValidationError("Los precios no pueden ser negativos.")

        plan = self._repo.get_by_id(cmd.id)
        plan.update(cmd)
        return plan
