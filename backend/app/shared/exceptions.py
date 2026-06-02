from fastapi import HTTPException


class DomainError(Exception):
    """Error de dominio — problema de negocio, no de infraestructura."""
    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        super().__init__(message)
        self.code = code


class NotFoundError(DomainError):
    def __init__(self, entity: str, entity_id: str):
        super().__init__(f"{entity} {entity_id} no encontrado", code="NOT_FOUND")
        self.entity = entity
        self.entity_id = entity_id


class TenantNotActiveError(DomainError):
    def __init__(self, tenant_id: str, estado: str):
        super().__init__(f"Tenant {tenant_id} no está activo (estado: {estado})", code="TENANT_NOT_ACTIVE")


class PlanLimitExceededError(DomainError):
    def __init__(self, tenant_id: str):
        super().__init__(
            f"Tenant {tenant_id} ha alcanzado el límite mensual de comprobantes",
            code="PLAN_LIMIT_EXCEEDED",
        )


class IdempotencyConflictError(DomainError):
    def __init__(self, idempotency_key: str):
        super().__init__(f"Idempotency key ya procesada: {idempotency_key}", code="IDEMPOTENCY_CONFLICT")


class InvalidCertificateError(DomainError):
    def __init__(self, reason: str):
        super().__init__(f"Certificado de firma inválido: {reason}", code="INVALID_CERTIFICATE")


class XmlValidationError(DomainError):
    def __init__(self, errors: list[str]):
        super().__init__(f"XML inválido según XSD del SRI: {'; '.join(errors)}", code="XML_VALIDATION_ERROR")
        self.errors = errors


class SriConnectionError(Exception):
    """Error de conexión con el SRI — puede ser transitorio."""
    pass


def domain_error_to_http(error: DomainError) -> HTTPException:
    status_map = {
        "NOT_FOUND": 404,
        "TENANT_NOT_ACTIVE": 403,
        "PLAN_LIMIT_EXCEEDED": 402,
        "IDEMPOTENCY_CONFLICT": 409,
        "INVALID_CERTIFICATE": 422,
        "XML_VALIDATION_ERROR": 422,
    }
    status = status_map.get(error.code, 400)
    return HTTPException(status_code=status, detail={"code": error.code, "message": str(error)})
