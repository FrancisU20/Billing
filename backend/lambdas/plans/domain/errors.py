from __future__ import annotations
from shared.errors import NotFoundError, ConflictError


class PlanNotFoundError(NotFoundError):
    code            = "PLAN_NOT_FOUND"
    default_message = "El plan no fue encontrado."


class PlanSlugExistsError(ConflictError):
    code            = "PLAN_SLUG_EXISTS"
    default_message = "Ya existe un plan con ese identificador."
