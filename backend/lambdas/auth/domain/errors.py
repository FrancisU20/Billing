from __future__ import annotations

"""Auth-specific errors."""

from shared.errors import AuthError, BusinessError


class InvalidChallengeResponseError(AuthError):
    code = "INVALID_CHALLENGE_RESPONSE"
    default_message = "La respuesta al challenge de autenticación no es válida."


class AuthChallengeFailedError(BusinessError):
    code = "AUTH_CHALLENGE_FAILED"
    default_message = "No se pudo completar el challenge de autenticación."
