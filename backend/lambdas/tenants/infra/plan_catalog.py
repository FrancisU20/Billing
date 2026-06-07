from __future__ import annotations

from lambdas.plans.domain.errors import PlanNotFoundError
from lambdas.plans.infra.plan_repository import DynamoPlanRepository
from lambdas.tenants.domain.repositories.i_plan_catalog import IPlanCatalog
from shared.errors import ValidationError


class DynamoPlanCatalog(IPlanCatalog):
    def __init__(self, plans_table) -> None:
        self._plans = DynamoPlanRepository(plans_table)

    def ensure_active(self, plan_id: str) -> None:
        if not plan_id:
            raise ValidationError("plan_id es requerido")

        try:
            plan = self._plans.get_by_id(plan_id)
        except PlanNotFoundError as exc:
            raise ValidationError("plan_id inválido") from exc

        if not plan.active:
            raise ValidationError("plan_id no está activo")
