import re
from decimal import Decimal

from lambdas.plans.domain.commands import CreatePlanCommand
from lambdas.plans.domain.errors import PlanNotFoundError, PlanSlugExistsError
from lambdas.plans.domain.plan import Plan
from lambdas.plans.domain.repositories.i_plan_repository import IPlanRepository
from shared.errors import ValidationError

_SLUG_RE      = re.compile(r"^[a-z0-9_-]{2,30}$")
_VALID_CYCLES = {"month", "year"}


class CreatePlanUseCase:
    def __init__(self, repo: IPlanRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CreatePlanCommand) -> Plan:
        if not _SLUG_RE.match(cmd.slug):
            raise ValidationError(
                "El slug debe tener 2-30 caracteres en minúsculas (a-z, 0-9, _, -)."
            )
        if cmd.limit_cycle not in _VALID_CYCLES:
            raise ValidationError("El ciclo de límite debe ser 'month' o 'year'.")
        if cmd.monthly_price < Decimal("0") or cmd.annual_price < Decimal("0"):
            raise ValidationError("Los precios no pueden ser negativos.")

        if self._slug_exists(cmd.slug):
            raise PlanSlugExistsError()

        return Plan.create(cmd)

    def _slug_exists(self, slug: str) -> bool:
        try:
            self._repo.get_by_slug(slug)
            return True
        except PlanNotFoundError:
            return False
