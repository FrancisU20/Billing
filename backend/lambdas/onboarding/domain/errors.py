from __future__ import annotations

from shared.errors import BusinessError, NotFoundError


class PlanNotFoundError(NotFoundError):
    code = "PLAN_NOT_FOUND"
    default_message = "El plan no fue encontrado."


class PlanNotActiveError(BusinessError):
    code = "PLAN_NOT_ACTIVE"
    default_message = "El plan seleccionado no está disponible."


class OnboardingVerificationNotFoundError(NotFoundError):
    code = "ONBOARDING_VERIFICATION_NOT_FOUND"
    default_message = "La verificación del registro no fue encontrada."


class OnboardingOtpInvalidError(BusinessError):
    code = "ONBOARDING_OTP_INVALID"
    default_message = "El código de verificación no es válido."


class OnboardingOtpExpiredError(BusinessError):
    code = "ONBOARDING_OTP_EXPIRED"
    default_message = "El código de verificación expiró. Solicita uno nuevo."


class OnboardingOtpAttemptsExceededError(BusinessError):
    code = "ONBOARDING_OTP_ATTEMPTS_EXCEEDED"
    default_message = "Se excedió el número de intentos. Solicita un código nuevo."


class OnboardingPayloadMismatchError(BusinessError):
    code = "ONBOARDING_PAYLOAD_MISMATCH"
    default_message = "Los datos del registro no coinciden con la verificación solicitada."


class OnboardingPaymentRequiredError(BusinessError):
    code = "ONBOARDING_PAYMENT_REQUIRED"
    default_message = "El plan seleccionado requiere un pago completado para completar el registro."


class OnboardingPaymentNotCapturedError(BusinessError):
    code = "ONBOARDING_PAYMENT_NOT_CAPTURED"
    default_message = "El pago no fue completado. Intenta de nuevo con un nuevo pago."


class OnboardingPaymentNotFoundError(BusinessError):
    code = "ONBOARDING_PAYMENT_NOT_FOUND"
    default_message = "No se encontró el pago indicado. Verifica el order_id."
