from __future__ import annotations

"""
Domain error hierarchy.

Rules:
- Every known error extends AppError with a unique `code` in SCREAMING_SNAKE_CASE.
- `default_message` is the Spanish message the end client will see.
- Never pass dynamic messages to the client — only code + default_message.
- The full stacktrace always goes to CloudWatch, never to the HTTP response.
"""


class AppError(Exception):
    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    default_message: str = "Ocurrió un error interno. Por favor intenta nuevamente."

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail
        super().__init__(self.code)


# ── 400 ───────────────────────────────────────────────────────────────────────


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 400
    default_message = "Los datos enviados no son válidos."


# ── 401 ───────────────────────────────────────────────────────────────────────


class AuthError(AppError):
    code = "UNAUTHORIZED"
    status_code = 401
    default_message = "No estás autenticado. Por favor inicia sesión."


class TokenExpiredError(AuthError):
    code = "TOKEN_EXPIRED"
    default_message = "La sesión ha expirado. Por favor inicia sesión nuevamente."


class InvalidCredentialsError(AuthError):
    code = "INVALID_CREDENTIALS"
    default_message = "Usuario o contraseña incorrectos."


class MissingTenantContextError(AuthError):
    code = "MISSING_TENANT_CONTEXT"
    default_message = "No se pudo determinar el contexto de la empresa."


# ── 403 ───────────────────────────────────────────────────────────────────────


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = 403
    default_message = "No tienes permisos para realizar esta acción."


# ── 404 ───────────────────────────────────────────────────────────────────────


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
    default_message = "El recurso solicitado no fue encontrado."


# ── 409 ───────────────────────────────────────────────────────────────────────


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409
    default_message = "Ya existe un registro con esos datos."


class IdempotencyInProgressError(ConflictError):
    code = "IDEMPOTENCY_IN_PROGRESS"
    default_message = "La operación ya está en proceso. Reintenta en unos segundos."


class IdempotencyKeyReusedError(ConflictError):
    code = "IDEMPOTENCY_KEY_REUSED"
    default_message = "La llave de idempotencia ya fue usada con otra operación."


# ── 422 ───────────────────────────────────────────────────────────────────────


class BusinessError(AppError):
    code = "BUSINESS_ERROR"
    status_code = 422
    default_message = "No se pudo completar la operación."


# ── 500 ───────────────────────────────────────────────────────────────────────


class InternalError(AppError):
    code = "INTERNAL_ERROR"
    status_code = 500
    default_message = "Ocurrió un error interno. Por favor intenta nuevamente."


class ExternalServiceError(InternalError):
    code = "EXTERNAL_SERVICE_ERROR"
    default_message = "Un servicio externo respondió con un error. Por favor intenta nuevamente."


# ── DynamoDB ──────────────────────────────────────────────────────────────────


class OptimisticLockError(ConflictError):
    code = "OPTIMISTIC_LOCK_ERROR"
    default_message = "El registro fue modificado por otro proceso. Por favor intenta nuevamente."


class DatabaseError(InternalError):
    code = "DATABASE_ERROR"
    default_message = "Error al acceder a la base de datos. Por favor intenta nuevamente."
