from shared.errors import ConflictError, NotFoundError, BusinessError


class TenantNotFoundError(NotFoundError):
    code            = "TENANT_NOT_FOUND"
    default_message = "La empresa no fue encontrada."


class TenantRucAlreadyExistsError(ConflictError):
    code            = "TENANT_RUC_ALREADY_EXISTS"
    default_message = "Ya existe una empresa registrada con ese RUC."


class TenantSuspendedError(BusinessError):
    code            = "TENANT_SUSPENDED"
    default_message = "La empresa está suspendida y no puede operar."


class TenantInactivoError(BusinessError):
    code            = "TENANT_INACTIVO"
    default_message = "La empresa está inactiva."


class AmbienteSriInvalidoError(BusinessError):
    code            = "AMBIENTE_SRI_INVALIDO"
    default_message = "El ambiente SRI indicado no es válido. Use 'pruebas' o 'produccion'."
