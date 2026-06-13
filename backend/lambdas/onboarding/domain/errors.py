from __future__ import annotations

from shared.errors import BusinessError, NotFoundError


class PlanNotFoundError(NotFoundError):
    code = "PLAN_NOT_FOUND"
    default_message = "El plan no fue encontrado."


class PlanNotActiveError(BusinessError):
    code = "PLAN_NOT_ACTIVE"
    default_message = "El plan seleccionado no está disponible."
