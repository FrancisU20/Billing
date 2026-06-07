from __future__ import annotations

from shared.errors import BusinessError, ConflictError, NotFoundError


class TenantNotFoundError(NotFoundError):
    code = "TENANT_NOT_FOUND"
    default_message = "La empresa no fue encontrada."


class TenantRucAlreadyExistsError(ConflictError):
    code = "TENANT_RUC_ALREADY_EXISTS"
    default_message = "Ya existe una empresa registrada con ese RUC."


class TenantSuspendedError(BusinessError):
    code = "TENANT_SUSPENDED"
    default_message = "La empresa está suspendida y no puede operar."


class TenantInactiveError(BusinessError):
    code = "TENANT_INACTIVE"
    default_message = "La empresa está inactiva."


class InvalidSriEnvironmentError(BusinessError):
    code = "INVALID_SRI_ENVIRONMENT"
    default_message = "El ambiente SRI indicado no es válido. Use 'testing' o 'production'."
